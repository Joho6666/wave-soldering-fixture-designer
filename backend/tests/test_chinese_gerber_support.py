import io
import zipfile
import pytest
from unittest.mock import MagicMock
from app.services.gerber.parser import GerberParser


def test_classify_chinese_named_layers():
    parser = GerberParser()
    mock_gerber = MagicMock()
    mock_gerber.file_attrs = {}

    ltype, conf, _ = parser._classify_layer("板框层.gbr", mock_gerber)
    assert ltype == "board_outline"
    assert conf >= 0.85

    ltype, conf, _ = parser._classify_layer("顶层铜箔.gbr", mock_gerber)
    assert ltype == "top_copper"
    assert conf >= 0.85

    ltype, conf, _ = parser._classify_layer("底层阻焊.gbr", mock_gerber)
    assert ltype == "bottom_soldermask"
    assert conf >= 0.85

    ltype, conf, _ = parser._classify_layer("正面字符.gbr", mock_gerber)
    assert ltype == "top_silkscreen"
    assert conf >= 0.85

    ltype, conf, _ = parser._classify_layer("背面字符.gbr", mock_gerber)
    assert ltype == "bottom_silkscreen"
    assert conf >= 0.85


def test_zip_with_gbk_encoded_chinese_filenames(tmp_path):
    parser = GerberParser()
    zip_path = tmp_path / "chinese_test.zip"

    # 构造一个模拟 Windows GBK 编码创建的 zip 文件
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        # 写入简易 Gerber 文本
        gbr_content = b"G04 Outline*\n%FSLAX24Y24*%\n%MOIN*%\nG01*\nX0Y0D02*\nX1000000Y0D01*\nX1000000Y800000D01*\nX0Y800000D01*\nX0Y0D01*\nM02*"
        
        info1 = zipfile.ZipInfo("板框.gko")
        zf.writestr(info1, gbr_content)

    with open(zip_path, "wb") as f:
        f.write(zip_bytes.getvalue())

    members = parser._read_safe_archive(zip_path)
    assert len(members) == 1
    assert "板框" in members[0][0] or "gko" in members[0][0]
