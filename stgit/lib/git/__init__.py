"""A Python class hierarchy wrapping a git repository and its contents."""
from stgit.run import Run
from .branch import Branch
from .date import Date
from .iw import (
    CheckoutException,
    IndexAndWorktree,
    MergeConflictException,
    MergeException,
)
from .objects import Blob, BlobData, Commit, CommitData, Tree, TreeData
from .person import Person
from .repository import Repository, RepositoryException

__all__ = [
    'Blob',
    'BlobData',
    'Branch',
    'CheckoutException',
    'Commit',
    'CommitData',
    'Date',
    'IndexAndWorktree',
    'MergeConflictException',
    'MergeException',
    'Person',
    'Repository',
    'RepositoryException',
    'Tree',
    'TreeData',
]
    return (
        Run('git', 'apply', '--stat', '--summary')
        .encoding(None)
        .raw_input(diff)
        .decoding('utf-8')
        .raw_output()
    )