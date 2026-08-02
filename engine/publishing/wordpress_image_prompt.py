from __future__ import annotations


def recommend_prompt(
    title: str,
    excerpt: str,
) -> str:
    title_value = title.strip()
    excerpt_value = excerpt.strip()

    if not title_value:
        raise ValueError(
            "Title is required for prompt recommendation."
        )

    return (
        "Create a refined legal editorial illustration for "
        f"the article titled '{title_value}'. "
        f"Context: {excerpt_value}. "
        "Use symbolic, non-photorealistic visual storytelling; "
        "avoid depicting identifiable real judges, litigants, "
        "victims, accused persons, or actual court events. "
        "Suitable for both WordPress and print."
    )


def polish_prompt(prompt: str) -> str:
    value = prompt.strip()

    if not value:
        raise ValueError(
            "Prompt cannot be empty."
        )

    return (
        f"{value} Improve composition, symbolism, legal clarity, "
        "print readability, and consistency with the "
        "LegalKural editorial identity."
    )
