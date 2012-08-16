#!/usr/bin/python

import argparse
import json
import os
import sys

from launchpadlib import uris
from launchpadlib.launchpad import Launchpad


APP_NAME = 'get-merge-queue'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache')


class UserError(Exception):
    """Errors safe to show the user."""


class LaunchpadError(UserError):
    """Errors raised by Launchpad."""

    def __init__(self, bad_request):
        super(LaunchpadError, self).__init__(
            "[%s] %s" % (bad_request.response['status'], bad_request.content))


def make_arg_parser():
    parser = argparse.ArgumentParser(
        description="Get merge proposals against a branch")
    parser.add_argument('branch', type=str, help="the branch")
    parser.add_argument('--pretty', action='store_true')
    parser.add_argument(
        '--lp-instance', choices=uris.service_roots,
        default='production',
        help=(
            'Which Launchpad instance to create the PPA on.  '
            'Defaults to production.'))
    return parser


def get_launchpad(service_root):
    return Launchpad.login_with(
        APP_NAME, service_root, CACHE_DIR, version="devel")


def _iter_merge_proposals(launchpad, branch_url):
    branch = launchpad.branches.getByUrl(url=branch_url)
    if branch is None:
        raise UserError("Not a valid branch: %r" % (branch_url,))
    for b in branch.landing_candidates:
        yield b


def lp_to_dict(lp_obj):
    lp_obj._ensure_representation()
    return dict(lp_obj._wadl_resource.representation)


def lp_to_dict_expanded(lp_obj, attributes):
    lp_dict = lp_to_dict(lp_obj)
    for attr in attributes:
        lp_dict[attr] = lp_to_dict(getattr(lp_obj, attr))
        del lp_dict['%s_link' % (attr,)]
    return lp_dict


def get_merge_proposals(launchpad, branch_url):
    for mp in _iter_merge_proposals(launchpad, branch_url):
        mp_dict = lp_to_dict(mp)
        mp_dict.update({'reviews': get_reviews(mp)})
        yield mp_dict


def get_reviews(mp):
    reviews = []
    for vote in mp.votes:
        review_dict = lp_to_dict_expanded(vote, ['comment', 'reviewer'])
        reviews.append(review_dict)
    return reviews


def main(args):
    parser = make_arg_parser()
    args = parser.parse_args(args)
    output = sys.stdout
    service_root = uris.service_roots[args.lp_instance]
    launchpad = get_launchpad(service_root)
    merge_proposals = list(get_merge_proposals(launchpad, args.branch))
    if args.pretty:
        json.dump(merge_proposals, output, indent=4, sort_keys=True)
    else:
        json.dump(merge_proposals, output)
    output.write('\n')


def run(args):
    try:
        main(args)
    except UserError, e:
        sys.stderr.write('ERROR: %s\n' % (e,))
        sys.stderr.flush()
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(run(sys.argv[1:]))
