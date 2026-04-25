"""Unit tests for migration verification helpers."""

from __future__ import annotations

from pathlib import Path

from itglue_migrate.verification import (
    AttachmentReference,
    EmbeddedImageReference,
    collect_embedded_image_references,
    verify_attachment_references,
    verify_embedded_images,
)


def test_verify_attachment_references_matches_clean_export(tmp_path: Path) -> None:
    attachment_dir = tmp_path / "attachments" / "configurations" / "123"
    attachment_dir.mkdir(parents=True)
    manual = attachment_dir / "manual.pdf"
    diagram = attachment_dir / "diagram.png"
    manual.write_bytes(b"PDF")
    diagram.write_bytes(b"PNG")

    result = verify_attachment_references(
        tmp_path,
        [
            AttachmentReference("configurations", "123", "manual.pdf", api_id="att-1"),
            AttachmentReference("configurations", "123", "diagram.png", api_id="att-2"),
        ],
    )

    assert result.ok is True
    assert result.expected_count == 2
    assert result.local_count == 2
    assert result.api_count == 2
    assert result.failures == []
    assert result.to_dict()["failures"] == []


def test_verify_attachment_references_reports_missing_file_and_count_mismatch(
    tmp_path: Path,
) -> None:
    attachment_dir = tmp_path / "attachments" / "configurations" / "123"
    attachment_dir.mkdir(parents=True)
    (attachment_dir / "manual.pdf").write_bytes(b"PDF")

    result = verify_attachment_references(
        tmp_path,
        [
            AttachmentReference("configurations", "123", "manual.pdf", api_id="att-1"),
            AttachmentReference("configurations", "123", "diagram.png", api_id="att-2"),
        ],
    )

    assert result.ok is False
    assert result.expected_count == 2
    assert result.local_count == 1
    assert result.api_count == 2
    assert [failure.category for failure in result.failures] == [
        "missing_file",
        "count_mismatch",
    ]


def test_verify_attachment_references_counts_only_expected_entities(
    tmp_path: Path,
) -> None:
    attachment_dir = tmp_path / "attachments" / "configurations" / "123"
    unrelated_dir = tmp_path / "attachments" / "configurations" / "999"
    attachment_dir.mkdir(parents=True)
    unrelated_dir.mkdir(parents=True)
    (attachment_dir / "manual.pdf").write_bytes(b"PDF")
    (unrelated_dir / "other.pdf").write_bytes(b"PDF")

    result = verify_attachment_references(
        tmp_path,
        [AttachmentReference("configurations", "123", "manual.pdf", api_id="att-1")],
    )

    assert result.ok is True
    assert result.local_count == 1


def test_verify_attachment_references_records_url_checker_exceptions(
    tmp_path: Path,
) -> None:
    attachment_dir = tmp_path / "attachments" / "configurations" / "123"
    attachment_dir.mkdir(parents=True)
    (attachment_dir / "manual.pdf").write_bytes(b"PDF")

    result = verify_attachment_references(
        tmp_path,
        [
            AttachmentReference(
                "configurations",
                "123",
                "manual.pdf",
                api_url="https://docs.example.invalid/manual.pdf",
            )
        ],
        url_checker=lambda _url: (_ for _ in ()).throw(TimeoutError("timeout")),
    )

    assert result.ok is False
    assert result.failures[0].category == "inaccessible_url"


def test_verify_embedded_images_reports_present_image(tmp_path: Path) -> None:
    doc_dir = tmp_path / "documents" / "DOC-1-200 HTML Document"
    doc_dir.mkdir(parents=True)
    image = doc_dir / "diagram.png"
    image.write_bytes(b"PNG")

    result = verify_embedded_images(
        [
            EmbeddedImageReference(
                document_id="200",
                source="diagram.png",
                resolved_path=image,
            )
        ],
    )

    assert result.ok is True
    assert result.expected_count == 1
    assert result.present_count == 1
    assert result.failures == []


def test_verify_embedded_images_reports_broken_image(tmp_path: Path) -> None:
    missing = tmp_path / "documents" / "DOC-1-200 HTML Document" / "missing.png"

    result = verify_embedded_images(
        [
            EmbeddedImageReference(
                document_id="200",
                source="missing.png",
                resolved_path=missing,
            )
        ],
    )

    assert result.ok is False
    assert result.expected_count == 1
    assert result.present_count == 0
    assert len(result.failures) == 1
    assert result.failures[0].category == "broken_embedded_image"


def test_verify_embedded_images_records_url_checker_exceptions(
    tmp_path: Path,
) -> None:
    image = tmp_path / "diagram.png"
    image.write_bytes(b"PNG")

    result = verify_embedded_images(
        [
            EmbeddedImageReference(
                document_id="200",
                source="diagram.png",
                resolved_path=image,
                migrated_url="https://docs.example.invalid/image.png",
            )
        ],
        url_checker=lambda _url: (_ for _ in ()).throw(TimeoutError("timeout")),
    )

    assert result.ok is False
    assert result.failures[0].category == "inaccessible_url"


def test_collect_embedded_image_references_from_export_html(tmp_path: Path) -> None:
    doc_dir = tmp_path / "documents" / "DOC-1-200 HTML Document"
    image_dir = doc_dir / "1" / "docs" / "200" / "images"
    image_dir.mkdir(parents=True)
    image = image_dir / "img123"
    image.write_bytes(b"PNG")
    (doc_dir / "index.html").write_text(
        '<p>diagram</p><img src="1/docs/200/images/img123">',
        encoding="utf-8",
    )

    references = collect_embedded_image_references(
        tmp_path,
        [{"id": "200", "name": "HTML Document"}],
    )

    assert len(references) == 1
    assert references[0].document_id == "200"
    assert references[0].source == "1/docs/200/images/img123"
    assert references[0].resolved_path == image.resolve()


def test_collect_embedded_image_references_skips_missing_document_ids(
    tmp_path: Path,
) -> None:
    assert collect_embedded_image_references(
        tmp_path,
        [{"id": None, "name": "Missing"}, {"name": "Also Missing"}],
    ) == []
