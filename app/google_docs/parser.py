"""Google Docs document parser for extracting structured content."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentElement:
    """Represents a structured element in a Google Docs document."""

    type: str  # paragraph, heading, list, table, etc.
    text: str
    level: int = 0  # For headings (1-6) or list nesting
    style: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSection:
    """Represents a section of a document with hierarchical structure."""

    title: str
    level: int
    elements: list[DocumentElement] = field(default_factory=list)
    subsections: list["DocumentSection"] = field(default_factory=list)

    def get_full_text(self) -> str:
        """Get all text content from this section and subsections."""
        text_parts = []

        # Add section title
        if self.title:
            text_parts.append(self.title)

        # Add element text
        for element in self.elements:
            if element.text.strip():
                text_parts.append(element.text.strip())

        # Add subsection text recursively
        for subsection in self.subsections:
            subsection_text = subsection.get_full_text()
            if subsection_text.strip():
                text_parts.append(subsection_text.strip())

        return "\n\n".join(text_parts)


@dataclass
class ParsedDocument:
    """Represents a fully parsed Google Docs document."""

    title: str
    document_id: str
    sections: list[DocumentSection] = field(default_factory=list)

    def get_full_text(self) -> str:
        """Get all text content from the document."""
        text_parts = []

        # Add document title
        if self.title:
            text_parts.append(self.title)

        # Add all sections
        for section in self.sections:
            section_text = section.get_full_text()
            if section_text.strip():
                text_parts.append(section_text.strip())

        return "\n\n".join(text_parts)


class GoogleDocsParser:
    """Parser for extracting structured content from Google Docs."""

    def __init__(self):
        """Initialize the parser."""
        pass

    def parse_document(self, document_data: dict[str, Any]) -> ParsedDocument:
        """Parse a Google Docs document into structured sections.

        Args:
            document_data: Raw document data from Google Docs API

        Returns:
            Parsed document with hierarchical structure
        """
        title = document_data.get("title", "Untitled")
        document_id = document_data.get("documentId", "")

        # Check if document has tabs (newer Google Docs feature)
        if "tabs" in document_data:
            print(f"📑 Document has {len(document_data['tabs'])} tabs")
            sections = self._parse_tabbed_document(document_data["tabs"])
        else:
            # Legacy single-tab document
            print("📄 Document uses legacy single-tab format")
            content = document_data.get("body", {}).get("content", [])
            sections = self._parse_content_into_sections(content)

        # If no sections were created, create a default section
        if not sections:
            sections = [DocumentSection(title="", level=0)]

        return ParsedDocument(title=title, document_id=document_id, sections=sections)

    def _parse_tabbed_document(self, tabs: list[dict[str, Any]]) -> list[DocumentSection]:
        """Parse a multi-tab Google Docs document.

        Args:
            tabs: List of tab objects from the Google Docs API

        Returns:
            List of sections from all tabs
        """
        all_sections = []

        for tab_index, tab in enumerate(tabs):
            # Get tab title and content
            tab_title = self._get_tab_title(tab)
            print(f"📑 Processing tab {tab_index + 1}: {tab_title}")

            # Parse content from this tab
            tab_sections = self._parse_single_tab(tab, tab_index)

            # Add tab title as a top-level section if it exists
            if tab_title and tab_sections:
                # Create a section for the tab itself
                tab_section = DocumentSection(
                    title=tab_title,
                    level=1,  # Top-level tab
                    elements=[],
                    subsections=tab_sections,
                )
                all_sections.append(tab_section)
            else:
                # Add sections directly if no tab title
                all_sections.extend(tab_sections)

            # Recursively parse child tabs
            if "childTabs" in tab:
                child_sections = self._parse_tabbed_document(tab["childTabs"])
                all_sections.extend(child_sections)

        return all_sections

    def _parse_single_tab(self, tab: dict[str, Any], tab_index: int) -> list[DocumentSection]:
        """Parse content from a single tab.

        Args:
            tab: Single tab object from the API
            tab_index: Index of the tab

        Returns:
            List of sections from this tab
        """
        # Get content from the documentTab
        document_tab = tab.get("documentTab", {})
        content = document_tab.get("body", {}).get("content", [])

        if not content:
            print(f"   ⚠️  Tab {tab_index + 1} has no content")
            return []

        # Parse the content into sections
        sections = self._parse_content_into_sections(content)
        print(f"   ✅ Found {len(sections)} sections in tab {tab_index + 1}")

        return sections

    def _get_tab_title(self, tab: dict[str, Any]) -> str:
        """Extract the title of a tab.

        Args:
            tab: Tab object from the API

        Returns:
            Tab title or empty string if none found
        """
        # Try to get tab title from various possible locations
        tab_properties = tab.get("tabProperties", {})

        # Check for title in tab properties
        if "title" in tab_properties:
            return tab_properties["title"]

        # Check for index-based title
        if "index" in tab_properties:
            return f"Tab {tab_properties['index'] + 1}"

        # Try to extract from first paragraph if no explicit title
        document_tab = tab.get("documentTab", {})
        content = document_tab.get("body", {}).get("content", [])

        for item in content:
            if "paragraph" in item:
                element = self._parse_paragraph(item["paragraph"])
                if element.text.strip():
                    # Use first non-empty paragraph as title if it's short
                    if len(element.text.strip()) < 100:
                        return element.text.strip()
                    break

        return ""

    def _parse_content_into_sections(self, content: list[dict[str, Any]]) -> list[DocumentSection]:
        """Parse document content into hierarchical sections."""
        sections = []
        current_section = None
        section_stack = []  # Stack to track nested sections

        for item in content:
            if "paragraph" in item:
                element = self._parse_paragraph(item["paragraph"])

                if element.type == "heading":
                    # Create new section for headings
                    new_section = DocumentSection(title=element.text, level=element.level)

                    # Handle section hierarchy
                    if element.level == 1:
                        # Top-level heading
                        sections.append(new_section)
                        section_stack = [new_section]
                        current_section = new_section
                    else:
                        # Nested heading - find parent section
                        while section_stack and section_stack[-1].level >= element.level:
                            section_stack.pop()

                        if section_stack:
                            # Add as subsection to parent
                            parent_section = section_stack[-1]
                            parent_section.subsections.append(new_section)
                        else:
                            # No parent found, add as top-level
                            sections.append(new_section)

                        section_stack.append(new_section)
                        current_section = new_section
                else:
                    # Regular content - add to current section
                    if current_section is None:
                        # No section yet, create a default one
                        current_section = DocumentSection(title="", level=0)
                        sections.append(current_section)
                        section_stack = [current_section]

                    current_section.elements.append(element)

            elif "table" in item:
                element = self._parse_table(item["table"])
                if current_section is None:
                    current_section = DocumentSection(title="", level=0)
                    sections.append(current_section)
                    section_stack = [current_section]
                current_section.elements.append(element)

        return sections

    def _parse_paragraph(self, paragraph: dict[str, Any]) -> DocumentElement:
        """Parse a paragraph element."""
        # Extract text content
        text_parts = []

        elements = paragraph.get("elements", [])
        for element in elements:
            if "textRun" in element:
                text_content = element["textRun"].get("content", "")
                text_parts.append(text_content)

        text = "".join(text_parts).strip()

        # Determine element type and level
        paragraph_style = paragraph.get("paragraphStyle", {})
        named_style_type = paragraph_style.get("namedStyleType", "")

        if named_style_type.startswith("HEADING_"):
            element_type = "heading"
            level = int(named_style_type.split("_")[1])
        elif named_style_type == "TITLE":
            element_type = "heading"
            level = 1
        elif named_style_type == "SUBTITLE":
            element_type = "heading"
            level = 2
        else:
            # Check if paragraph looks like a heading based on text style
            element_type = "paragraph"
            level = 0

            # Check for question marks as heading indicators
            if text.strip().endswith("?") and len(text.strip()) < 200:
                # Check if any part of the text is bold or has special formatting
                for element in elements:
                    if "textRun" in element:
                        text_style = element["textRun"].get("textStyle", {})
                        # Check for bold, or special background color (yellow highlighting)
                        background_color = (
                            text_style.get("backgroundColor", {})
                            .get("color", {})
                            .get("rgbColor", {})
                        )
                        if text_style.get("bold", False) or background_color.get("green") == 1:
                            element_type = "heading"
                            level = 3  # Treat as a level 3 heading
                            break

        return DocumentElement(type=element_type, text=text, level=level, style=paragraph_style)

    def _parse_table(self, table: dict[str, Any]) -> DocumentElement:
        """Parse a table element."""
        # Extract table content as text
        text_parts = []

        table_rows = table.get("tableRows", [])
        for row in table_rows:
            row_cells = []
            for cell in row.get("tableCells", []):
                cell_content = cell.get("content", [])
                cell_text = self._extract_text_from_content(cell_content)
                if cell_text.strip():
                    row_cells.append(cell_text.strip())

            if row_cells:
                text_parts.append(" | ".join(row_cells))

        table_text = "\n".join(text_parts)

        return DocumentElement(
            type="table",
            text=table_text,
            level=0,
            metadata={"columns": len(table_rows[0].get("tableCells", [])) if table_rows else 0},
        )

    def _extract_text_from_content(self, content: list[dict[str, Any]]) -> str:
        """Extract text from content elements."""
        text_parts = []

        for item in content:
            if "paragraph" in item:
                elements = item["paragraph"].get("elements", [])
                for element in elements:
                    if "textRun" in element:
                        text_content = element["textRun"].get("content", "")
                        text_parts.append(text_content)

        return "".join(text_parts)
