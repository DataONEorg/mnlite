import json
import scrapy.http
import soscan.spiders.apijsonldspider


def fake_json_response(url, payload):
    request = scrapy.http.Request(url=url)
    return scrapy.http.TextResponse(
        url=url,
        status=200,
        request=request,
        body=json.dumps(payload).encode("utf-8"),
        encoding="utf-8",
    )


def fake_text_response(url, status=200, body=""):
    request = scrapy.http.Request(url=url)
    return scrapy.http.TextResponse(
        url=url,
        status=status,
        request=request,
        body=body.encode("utf-8"),
        encoding="utf-8",
    )


def test_parse_page_yields_items_and_next_request():
    spider = soscan.spiders.apijsonldspider.APIJsonldSpider(
        sitemap_urls=["https://example.org/api/datasets?page=1"],
        api_records_path="items",
        api_next_path="next",
        api_jsonld_field="jsonld",
        api_url_field="url",
        api_modified_field="modified",
    )
    response = fake_json_response(
        "https://example.org/api/datasets?page=1",
        {
            "items": [
                {
                    "url": "https://example.org/dataset/1",
                    "modified": "2026-02-01T12:00:00Z",
                    "jsonld": {
                        "@context": "https://schema.org",
                        "@type": "Dataset",
                        "name": "Dataset One",
                        "identifier": "doi:10.1234/example.1",
                    },
                },
                {
                    "url": "/dataset/2",
                    "modified": "2026-02-02T12:00:00Z",
                    "jsonld": {
                        "@context": "https://schema.org",
                        "@type": "Dataset",
                        "name": "Dataset Two",
                        "identifier": "doi:10.1234/example.2",
                    },
                },
            ],
            "next": "?page=2",
        },
    )

    results = list(spider.parse_page(response))

    assert len(results) == 3
    assert results[0]["url"] == "https://example.org/dataset/1"
    assert results[0]["jsonld"]["@type"] == "Dataset"
    assert results[1]["url"] == "https://example.org/dataset/2"
    assert isinstance(results[2], scrapy.http.Request)
    assert results[2].url == "https://example.org/api/datasets?page=2"


def test_parse_page_applies_lastmod_filter_and_count_only():
    spider = soscan.spiders.apijsonldspider.APIJsonldSpider(
        sitemap_urls=["https://example.org/api/datasets"],
        api_records_path="items",
        api_next_path="next",
        api_jsonld_field="jsonld",
        api_url_field="url",
        api_modified_field="modified",
        lastmod_filter="2026-02-01T00:00:00Z",
        count_only=True,
    )
    response = fake_json_response(
        "https://example.org/api/datasets",
        {
            "items": [
                {
                    "url": "https://example.org/dataset/old",
                    "modified": "2026-01-01T00:00:00Z",
                    "jsonld": {"@type": "Dataset", "name": "Old"},
                },
                {
                    "url": "https://example.org/dataset/new",
                    "modified": "2026-02-03T00:00:00Z",
                    "jsonld": {"@type": "Dataset", "name": "New"},
                },
            ],
            "next": None,
        },
    )

    results = list(spider.parse_page(response))

    assert len(results) == 1
    assert results[0]["url"] == "https://example.org/dataset/new"
    assert results[0]["source"] == "https://example.org/api/datasets"


def test_page_param_pagination_increments_until_stop_status():
    spider = soscan.spiders.apijsonldspider.APIJsonldSpider(
        sitemap_urls=["https://example.org/api/datasets"],
        api_page_param="page",
        api_next_path="missing_next",
        api_records_path="items",
        api_jsonld_field="jsonld",
        api_stop_status_codes=[404],
    )

    first_page = fake_json_response(
        "https://example.org/api/datasets?page=1",
        {
            "items": [
                {
                    "url": "https://example.org/dataset/1",
                    "jsonld": {
                        "@context": "https://schema.org",
                        "@type": "Dataset",
                        "name": "Dataset One",
                    },
                }
            ]
        },
    )
    first_page.meta["api_base_url"] = "https://example.org/api/datasets"
    first_page.meta["api_page"] = 1

    results = list(spider.parse_page(first_page))
    assert len(results) == 2
    assert results[0]["url"] == "https://example.org/dataset/1"
    assert isinstance(results[1], scrapy.http.Request)
    assert results[1].url == "https://example.org/api/datasets?page=2"

    stop_page = fake_text_response("https://example.org/api/datasets?page=3", status=404)
    stopped = list(spider.parse_page(stop_page))
    assert stopped == []


def test_page_param_pagination_continues_when_all_items_filtered_by_lastmod():
    spider = soscan.spiders.apijsonldspider.APIJsonldSpider(
        sitemap_urls=["https://example.org/api/datasets"],
        api_page_param="page",
        api_next_path="missing_next",
        api_records_path="items",
        api_jsonld_field="jsonld",
        api_modified_field="modified",
        lastmod_filter="2026-02-01T00:00:00Z",
    )

    # All items on this page are older than lastmod_filter and should be skipped,
    # but pagination via page parameter should still continue to the next page.
    first_page = fake_json_response(
        "https://example.org/api/datasets?page=1",
        {
            "items": [
                {
                    "url": "https://example.org/dataset/old-1",
                    "modified": "2026-01-01T00:00:00Z",
                    "jsonld": {
                        "@context": "https://schema.org",
                        "@type": "Dataset",
                        "name": "Old Dataset One",
                    },
                },
                {
                    "url": "https://example.org/dataset/old-2",
                    "modified": "2026-01-15T00:00:00Z",
                    "jsonld": {
                        "@context": "https://schema.org",
                        "@type": "Dataset",
                        "name": "Old Dataset Two",
                    },
                },
            ]
        },
    )
    first_page.meta["api_base_url"] = "https://example.org/api/datasets"
    first_page.meta["api_page"] = 1

    results = list(spider.parse_page(first_page))

    # No items should be yielded because all were filtered out by lastmod_filter,
    # but a Request for the next page should still be emitted.
    assert all(not isinstance(r, dict) or "url" not in r or "Old Dataset" not in str(r) for r in results)
    assert len(results) == 1
    assert isinstance(results[0], scrapy.http.Request)
    assert results[0].url == "https://example.org/api/datasets?page=2"