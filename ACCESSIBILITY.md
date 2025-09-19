# Accessibility Statement and Guidelines for Paleae

Paleae is committed to building and maintaining an inclusive and accessible tool. We believe that software should be usable by everyone, regardless of their abilities or the assistive technologies they use.

This document outlines our commitment to accessibility and provides guidelines for contributors to ensure that all changes maintain or improve the accessibility of Paleae and its related assets (like the website and documentation).

## Our Commitment

We strive to adhere to the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards for our website and documentation. For the `paleae.py` tool itself, our focus is on ensuring its output is machine-readable and compatible with various parsing and analysis tools, including those used by assistive technologies.

## Guidelines for Contributors

When contributing to Paleae, please keep accessibility in mind:

### Code Contributions (`paleae.py`)

*   **Output Clarity:** Ensure any new output or changes to existing output are clear, concise, and structured. Avoid ambiguous or overly complex text that might be difficult for screen readers or other assistive tools to parse.
*   **Error Messages:** Make error messages informative and actionable. They should clearly explain what went wrong and, if possible, how to resolve it.
*   **CLI Usability:** Consider keyboard navigation and screen reader compatibility for any interactive CLI elements (though Paleae is primarily a non-interactive tool).

### Website (`index.html`)

*   **Semantic HTML:** Use HTML elements for their intended purpose (e.g., `<button>` for buttons, `<h1>` for main headings). This provides a logical structure for assistive technologies.
*   **Color Contrast:** Ensure all text and interactive elements have sufficient color contrast against their background. We aim for WCAG 2.1 AA standards (minimum 4.5:1 for normal text, 3:1 for large text).
*   **Alternative Text:** Provide meaningful `alt` text for all images (`<img alt="...">`). If an image is purely decorative, use `alt=""` or `aria-hidden="true"`.
*   **Keyboard Navigation:** Ensure all interactive elements (buttons, links, form fields) are reachable and operable using only the keyboard (Tab, Enter, Spacebar).
*   **ARIA Attributes:** Use ARIA attributes (`aria-label`, `aria-labelledby`, `role`, `aria-hidden`) judiciously to enhance semantics where native HTML is insufficient.
*   **Responsive Design:** Ensure the website is usable and readable across various screen sizes and devices.

### Documentation (Wiki, `README.md`, etc.)

*   **Clear Language:** Write clearly and concisely. Avoid jargon where possible, or explain it.
*   **Headings:** Use proper heading hierarchy (`#`, `##`, `###`) to structure content logically.
*   **Link Text:** Make link text descriptive (e.g., "Read our Contributing Guide" instead of "Click here").
*   **Code Blocks:** Ensure code blocks are readable and can be easily copied.

## Reporting Accessibility Issues

If you encounter any accessibility barriers while using Paleae, its website, or documentation, please report them via [GitHub Issues](https://github.com/PaulTiffany/paleae/issues). We take all feedback seriously and are committed to continuous improvement.

Thank you for helping us make Paleae accessible to everyone!