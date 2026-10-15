from apps.core.pagination import StandardPagination


def test_standard_pagination_page_size():
    pagination = StandardPagination()
    assert pagination.page_size == 50


def test_standard_pagination_page_size_query_param():
    pagination = StandardPagination()
    assert pagination.page_size_query_param == "page_size"


def test_standard_pagination_max_page_size():
    pagination = StandardPagination()
    assert pagination.max_page_size == 200
