from rest_framework.pagination import PageNumberPagination


class PaginacionEstandar(PageNumberPagination):
    """Paginación por número de página; el cliente puede pedir `?page_size=` hasta 100."""

    page_size_query_param = "page_size"
    max_page_size = 100
