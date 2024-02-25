class NotARepo(Exception):
    "Raised when the current directory is not a git repository."

    pass


class InvalidTree(Exception):
    "Raised when the tree is not valid."

    pass


class NoDiffs(Exception):
    "Raised when there are no diffs to review."

    pass


class NotAncestor(Exception):
    "Raised when the tree is not an ancestor of the HEAD."

    pass


class IsAncestor(Exception):
    "Raised when the tree is an ancestor of the HEAD."

    pass
