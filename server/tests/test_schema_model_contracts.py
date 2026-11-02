"""
Response schemas must read the attribute names their ORM models really have.
Found in QA against production data: three public endpoints returned HTTP 500
because the schema asked for `category` / `display_order` while the models
call them `faq_category` / `system_category` / `sort_order`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.models.enums import BudgetCategory, FAQCategory
from app.schemas.budgets.response import BudgetCategoryDefinitionResponse
from app.schemas.common.response import FAQResponse
from app.services.occasions.service import OccasionCategoryResponse


def test_faq_reads_faq_category_and_still_emits_category():
    faq = SimpleNamespace(id=uuid.uuid4(), question="Q?", answer="A", faq_category=FAQCategory.BOOKING,
                          is_active=True, display_order=1, helpful_count=0, not_helpful_count=0,
                          created_at=datetime.now(timezone.utc))
    out = FAQResponse.model_validate(faq)
    assert out.category == "booking" or out.category == FAQCategory.BOOKING
    assert "category" in out.model_dump() and "faq_category" not in out.model_dump()


def test_occasion_category_reads_sort_order_and_still_emits_display_order():
    row = SimpleNamespace(id=uuid.uuid4(), name="Festivals", description=None, icon_url=None, sort_order=3,
                          is_active=True, created_at=datetime.now(timezone.utc))
    out = OccasionCategoryResponse.model_validate(row)
    assert out.display_order == 3 and out.model_dump()["display_order"] == 3


def test_budget_category_accepts_system_and_custom_categories():
    base = dict(id=uuid.uuid4(), name="Decor", slug="decor", icon_url=None, description=None,
                is_active=True, display_order=1)
    system = BudgetCategoryDefinitionResponse.model_validate(SimpleNamespace(system_category=BudgetCategory.DECORATION, **base))
    custom = BudgetCategoryDefinitionResponse.model_validate(SimpleNamespace(system_category=None, **base))
    assert system.category == BudgetCategory.DECORATION
    assert custom.category is None


@pytest.mark.asyncio
async def test_creating_an_occasion_category_maps_fields_and_makes_a_unique_slug(monkeypatch):
    from app.services.occasions.service import OccasionCategoryCreate, OccasionService

    taken = {"festivals"}
    created = {}

    class _Col:
        def __eq__(self, other):  # SQLAlchemy builds a clause here; the fake just returns the value
            return other

    class Cats:
        _model = SimpleNamespace(slug=_Col())

        async def find_one(self, clause):
            return SimpleNamespace() if clause in taken else None

        async def create_from_dict(self, d):
            created.update(d)
            return SimpleNamespace(id=uuid.uuid4(), name=d["name"], description=None, icon_url=None,
                                   sort_order=d["sort_order"], is_active=True, created_at=datetime.now(timezone.utc))

    class Uow:
        occasions = SimpleNamespace(categories=Cats())

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

    svc = OccasionService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(), raising=False)
    out = await svc.create_category(OccasionCategoryCreate(name="Festivals", display_order=4))
    assert created["slug"] == "festivals-2"        # first slug was taken
    assert created["sort_order"] == 4 and "display_order" not in created
    assert out.display_order == 4


# ── Every response schema against its model ──────────────────────────────────

def _response_schema_pairs():
    import importlib
    import inspect
    import pkgutil

    from pydantic import BaseModel

    import app.schemas as schemas_pkg
    from app.models.base import Base

    models = {m.class_.__name__: m.class_ for m in Base.registry.mappers}
    pairs = []
    for mod in pkgutil.walk_packages(schemas_pkg.__path__, "app.schemas."):
        try:
            module = importlib.import_module(mod.name)
        except Exception:
            continue
        for name, obj in vars(module).items():
            if (
                inspect.isclass(obj) and issubclass(obj, BaseModel) and obj.__module__ == mod.name
                and name.endswith("Response") and obj.model_config.get("from_attributes")
                and name[:-8] in models
            ):
                pairs.append(pytest.param(obj, models[name[:-8]], id=f"{mod.name.split('.')[-2]}.{name}"))
    return pairs


@pytest.mark.parametrize("schema,model", _response_schema_pairs())
def test_response_schema_only_requires_attributes_its_model_has(schema, model):
    """
    `Schema.model_validate(row)` is how services build responses. A required
    field the model doesn't have turns into an HTTP 500 the first time a real
    row exists (the tables behind most of these were empty, so it was invisible).

    Only "field required" is asserted: the sample values here are generic, so
    type complaints about them (a JSON column sampled as {} for a list field,
    a free string for an enum) are noise, not defects.
    """
    from pydantic import ValidationError

    from tests.contract_helpers import build_row

    try:
        schema.model_validate(build_row(model))
    except ValidationError as exc:
        missing = [".".join(map(str, e["loc"])) for e in exc.errors() if e["type"] == "missing"]
        assert not missing, f"{schema.__name__} requires {missing} but {model.__name__} has no such attribute"


# ── Write paths: the API's names vs the model's columns ──────────────────────

def test_vendor_document_and_bank_renames():
    from app.services.vendors.service import _BANK_COLUMNS, _DOCUMENT_COLUMNS, _to_columns

    assert _to_columns({"document_type": "gst", "document_url": "https://x/y.pdf"}, _DOCUMENT_COLUMNS) == {
        "document_type": "gst", "file_url": "https://x/y.pdf"}
    assert _to_columns({"bank_name": "HDFC", "branch_name": "Andheri"}, _BANK_COLUMNS) == {
        "bank_name": "HDFC", "bank_branch": "Andheri"}


def test_every_renamed_column_really_exists_on_the_model():
    from app.models.base import Base
    from app.services.common.service import _BANNER_COLUMNS
    from app.services.vendors.service import _BANK_COLUMNS, _DOCUMENT_COLUMNS

    models = {m.class_.__name__: m.class_ for m in Base.registry.mappers}
    for model, renames in (("VendorDocument", _DOCUMENT_COLUMNS), ("VendorBankAccount", _BANK_COLUMNS), ("Banner", _BANNER_COLUMNS)):
        for column in renames.values():
            assert hasattr(models[model], column), f"{model} has no column {column}"


def test_the_app_can_submit_reviews_and_apply_referrals_without_server_only_fields():
    """The Flutter app never sends package_id / reviewer_id / referred_user_id."""
    from app.schemas.packages.create import PackageItemReviewCreate, PackageReviewCreate
    from app.schemas.referrals.create import ReferralApplyCreate
    from app.schemas.vendors.create import VendorReviewCreate

    booking = uuid.uuid4()
    assert PackageReviewCreate(booking_id=booking, rating=5, title="Great").rating == 5
    assert PackageItemReviewCreate(rating=4).rating == 4
    assert VendorReviewCreate(booking_id=booking, rating=5).rating == 5
    assert ReferralApplyCreate(referral_code="TYO1234").referral_code == "TYO1234"


@pytest.mark.asyncio
async def test_a_client_cannot_review_as_someone_else(monkeypatch):
    """A body naming another reviewer is discarded; the signed-in user wins."""
    from app.schemas.packages.create import PackageReviewCreate
    from app.services.packages.service import PackageService

    me, impostor = uuid.uuid4(), uuid.uuid4()
    created = {}

    class Reviews:
        async def create_from_dict(self, payload):
            created.update(payload)
            raise RuntimeError("stop after the payload is built")

    class Uow:
        packages = SimpleNamespace(reviews=Reviews())

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

    async def noop(*a, **k):
        return None

    monkeypatch.setattr("app.services.packages.service.validate_package_exists", noop)
    monkeypatch.setattr("app.services.packages.service.validate_review_not_duplicate", noop)
    svc = PackageService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(), raising=False)
    body = PackageReviewCreate(booking_id=uuid.uuid4(), rating=5, reviewer_id=impostor)
    with pytest.raises(RuntimeError):
        await svc.add_review(package_id=uuid.uuid4(), reviewer_id=me, data=body)
    assert created["customer_id"] == me and "reviewer_id" not in created
