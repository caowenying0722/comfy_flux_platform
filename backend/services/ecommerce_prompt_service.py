from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRODUCT_PRESERVATION_PROMPT = (
    "preserve the original product shape, preserve product color, preserve visible logo if present, "
    "keep product as the main subject, keep product recognizable, realistic product details, no extra product, no generated text"
)

PRODUCT_PRESERVATION_NEGATIVE = (
    "changed product identity, changed product label, fake text, misspelled text, extra product, missing product, "
    "duplicate product, warped packaging, broken geometry, unrealistic material"
)


@dataclass(frozen=True)
class EcommercePrompt:
    template_id: str
    template_name: str
    industry: str
    industry_name: str
    brand_tone: str
    brand_tone_name: str
    prompt: str
    negative_prompt: str
    workflow_json: str


class EcommercePromptService:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("prompts/ecommerce")
        self.templates = self._load("templates.json")
        self.industries = self._load("industries.json")
        self.brand_tones = self._load("brand_tones.json")

    def _load(self, name: str) -> dict[str, Any]:
        path = self.root / name
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def options(self) -> dict[str, list[dict[str, str]]]:
        return {
            "templates": self._options(self.templates),
            "industries": self._options(self.industries),
            "brand_tones": self._options(self.brand_tones),
        }

    @staticmethod
    def _options(items: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "id": item_id,
                "name": item.get("name", item_id),
                "description": item.get("description", ""),
            }
            for item_id, item in items.items()
        ]

    def compose(self, *, template_id: str, industry: str, brand_tone: str, extra_prompt: str = "") -> EcommercePrompt:
        template = self._get(self.templates, template_id, "template_id")
        industry_item = self._get(self.industries, industry, "industry")
        tone_item = self._get(self.brand_tones, brand_tone, "brand_tone")

        prompt_parts = [
            template["prompt"],
            industry_item["prompt"],
            tone_item["prompt"],
            PRODUCT_PRESERVATION_PROMPT,
        ]
        if extra_prompt.strip():
            prompt_parts.append(extra_prompt.strip())

        negative_parts = [
            template.get("negative_prompt", ""),
            PRODUCT_PRESERVATION_NEGATIVE,
        ]

        return EcommercePrompt(
            template_id=template_id,
            template_name=template.get("name", template_id),
            industry=industry,
            industry_name=industry_item.get("name", industry),
            brand_tone=brand_tone,
            brand_tone_name=tone_item.get("name", brand_tone),
            prompt=", ".join(part for part in prompt_parts if part),
            negative_prompt=", ".join(part for part in negative_parts if part),
            workflow_json=template["workflow_json"],
        )

    @staticmethod
    def _get(items: dict[str, Any], key: str, field_name: str) -> dict[str, Any]:
        try:
            return items[key]
        except KeyError as exc:
            valid = ", ".join(sorted(items))
            raise ValueError(f"invalid {field_name}: {key}. valid values: {valid}") from exc
