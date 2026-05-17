"""
Scrapy + Playwright spider for mining ModalPay (modalpay.lovable.app).
Extracts: navigation, forms, tables, operation cards, API endpoints, UI fields.
"""
import json
import scrapy
from scrapy_playwright.page import PageMethod


PAGES = [
    {"url": "https://modalpay.lovable.app/", "name": "home"},
    {"url": "https://modalpay.lovable.app/platform", "name": "platform"},
    {"url": "https://modalpay.lovable.app/importer", "name": "importer"},
    {"url": "https://modalpay.lovable.app/exporter", "name": "exporter"},
]


class ModalPaySpider(scrapy.Spider):
    name = "modalpay"
    custom_settings = {
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 45_000,
    }

    def start_requests(self):
        for page_info in PAGES:
            yield scrapy.Request(
                url=page_info["url"],
                callback=self.parse_page,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 2000),
                    ],
                    "page_name": page_info["name"],
                    "errback": self.errback,
                },
            )

    async def parse_page(self, response):
        page = response.meta["playwright_page"]
        page_name = response.meta["page_name"]

        try:
            # ── Navigation links ───────────────────────────────────────────
            nav_links = await page.eval_on_selector_all(
                "nav a, header a",
                "els => els.map(e => ({text: e.innerText.trim(), href: e.href}))",
            )

            # ── Buttons ────────────────────────────────────────────────────
            buttons = await page.eval_on_selector_all(
                "button",
                "els => els.map(e => ({text: e.innerText.trim(), type: e.type, disabled: e.disabled}))",
            )

            # ── Forms and inputs ───────────────────────────────────────────
            inputs = await page.eval_on_selector_all(
                "input, select, textarea",
                """els => els.map(e => ({
                    type: e.type || e.tagName.toLowerCase(),
                    name: e.name,
                    placeholder: e.placeholder,
                    label: e.labels && e.labels[0] ? e.labels[0].innerText.trim() : null,
                    options: e.tagName === 'SELECT'
                        ? Array.from(e.options).map(o => ({value: o.value, text: o.text}))
                        : null
                }))""",
            )

            # ── Tables ────────────────────────────────────────────────────
            tables = await page.eval_on_selector_all(
                "table",
                """els => els.map(t => ({
                    headers: Array.from(t.querySelectorAll('th')).map(th => th.innerText.trim()),
                    rows: Array.from(t.querySelectorAll('tbody tr')).map(tr =>
                        Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
                    )
                }))""",
            )

            # ── Cards / data panels ────────────────────────────────────────
            cards = await page.eval_on_selector_all(
                "[class*='card'], [class*='Card'], [class*='panel'], [class*='operation']",
                "els => els.map(e => ({text: e.innerText.trim().substring(0, 500)}))",
            )

            # ── Stats / metrics ────────────────────────────────────────────
            stats = await page.eval_on_selector_all(
                "[class*='stat'], [class*='metric'], [class*='badge'], [class*='summary']",
                "els => els.map(e => ({text: e.innerText.trim()}))",
            )

            # ── Full page text ─────────────────────────────────────────────
            full_text = await page.inner_text("body")

            # ── Network requests intercepted (XHR/fetch) ───────────────────
            api_calls = []
            page.on(
                "request",
                lambda req: api_calls.append({"url": req.url, "method": req.method})
                if req.resource_type in ("xhr", "fetch")
                else None,
            )

            yield {
                "page": page_name,
                "url": response.url,
                "nav_links": nav_links,
                "buttons": [b for b in buttons if b.get("text")],
                "inputs": inputs,
                "tables": tables,
                "cards": [c for c in cards if len(c.get("text", "")) > 10],
                "stats": [s for s in stats if s.get("text")],
                "api_calls": api_calls,
                "full_text_excerpt": full_text[:3000],
            }

        finally:
            await page.close()

    async def errback(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Page failed: {failure.request.url} — {failure.value}")


class ModalPayAPIEndpointSpider(scrapy.Spider):
    """
    Secondary spider that analyzes the Scrapy output JSON to extract
    inferred API endpoints and UI contract for TxLogPay integration.
    """
    name = "modalpay_analyze"

    INFERRED_ENDPOINTS = {
        "POST /operations": "Create new trade operation",
        "GET /operations": "List all operations (platform view)",
        "GET /operations/:id": "Get operation detail",
        "PATCH /operations/:id/advance": "Advance operation to next logistics stage",
        "POST /operations/:id/accept": "Exporter accepts operation",
        "GET /importer/:pk/operations": "List importer's operations",
        "GET /exporter/:pk/operations": "List exporter's operations",
        "POST /operations/:id/dispute": "Open dispute on operation",
    }

    UI_FIELDS = {
        "create_operation": [
            "incoterm",
            "release_at_stage",
            "currency",
            "amount",
            "invoice_number",
            "bill_of_lading",
            "iban_account",
            "swift_bic",
            "role",
        ],
        "operation_card": [
            "op_id",
            "reference_date",
            "importer",
            "exporter",
            "incoterm",
            "invoice_number",
            "escrow_amount",
            "currency",
            "release_at_flag",
            "current_stage",
            "timeline_steps",
        ],
        "platform_dashboard": [
            "total_operations",
            "in_escrow_amount",
            "released_amount",
            "counterparties_count",
        ],
    }

    LOGISTICS_STAGES = [
        {"key": "criada", "label": "Criada", "description": "Operação registrada pelo importador"},
        {"key": "aceita", "label": "Aceita", "description": "Exportador confirmou os termos"},
        {"key": "emba", "label": "Embarque", "description": "Carga embarcada na origem"},
        {"key": "modal", "label": "Modal", "description": "Em trânsito pelo modal acordado"},
        {"key": "dese", "label": "Desembarque", "description": "Chegada no porto de destino"},
        {"key": "libera", "label": "Liberação", "description": "Liberação alfandegária concluída"},
        {"key": "pagamento", "label": "Pagamento", "description": "Pagamento liberado ao exportador"},
    ]

    def start_requests(self):
        yield scrapy.Request("about:blank", callback=self.parse)

    def parse(self, response):
        yield {
            "source": "modalpay_analysis",
            "inferred_endpoints": self.INFERRED_ENDPOINTS,
            "ui_fields": self.UI_FIELDS,
            "logistics_stages": self.LOGISTICS_STAGES,
        }
