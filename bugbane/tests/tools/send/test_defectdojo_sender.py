from typing import Iterable
import pytest

from bugbane.tools.send.dd_api.abc import DefectDojoAPI
from bugbane.tools.send.defectdojo_sender import DefectDojoSender


@pytest.mark.parametrize(
    "tsp, old_path, new_path",
    [
        (["old->new"], "/old/mysample", "/new/mysample"),
        (["nonexistent->new"], "/old/mysample", "/old/mysample"),
        (["/old/->../new/"], "/old/mysample", "../new/mysample"),
        (["/old/->"], "/old/mysample", "mysample"),
        (["->new/"], "mysample", "new/mysample"),
        (["->"], "mysample", "mysample"),  # ignored, as both sides are empty
    ],
)
def test_translate_sample_path(
    tsp: Iterable[str], old_path: str, new_path: str
) -> None:
    api: DefectDojoAPI = None  # pyright: ignore
    sender = DefectDojoSender(
        api=api, cards_file_path="", translate_sample_paths_arg=tsp
    )
    assert sender.translate_sample_path(path=old_path) == new_path
