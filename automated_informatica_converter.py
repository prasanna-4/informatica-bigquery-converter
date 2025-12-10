"""
Fully Automated Informatica to BigQuery Converter
Author: Laxmi Prasanna Ravikanti

This script automates the ENTIRE workflow:
1. Reads Informatica XML
2. Converts to Markdown
3. Sends to Claude API automatically
4. Receives SQL + Lineage
5. Saves output files

NO MANUAL COPY/PASTE NEEDED!

Usage:
    python automated_informatica_converter.py input_mapping.xml

Requirements:
    pip install anthropic
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import argparse
import os
import sys
from datetime import datetime


class InformaticaXMLParser:
    """Parse Informatica XML and convert to structured Markdown"""
    
    def __init__(self, xml_content: str):
        self.xml_content = xml_content
        self.root = None
        self.parse_xml()
    
    def parse_xml(self):
        """Parse the XML content"""
        try:
            self.root = ET.fromstring(self.xml_content)
        except ET.ParseError as e:
            print(f"Error parsing XML: {e}")
            raise
    
    def extract_sources(self) -> List[Dict]:
        """Extract all source definitions"""
        sources = []
        for src in self.root.findall('.//SOURCE'):
            source_info = {
                'name': src.get('NAME', 'Unknown'),
                'database': src.get('DATABASETYPE', 'Unknown'),
                'fields': []
            }
            
            for field in src.findall('.//SOURCEFIELD'):
                field_info = {
                    'name': field.get('NAME'),
                    'datatype': field.get('DATATYPE', 'Unknown'),
                    'precision': field.get('PRECISION', ''),
                    'scale': field.get('SCALE', '')
                }
                source_info['fields'].append(field_info)
            
            sources.append(source_info)
        
        return sources
    
    def extract_transformations(self) -> List[Dict]:
        """Extract all transformation logic"""
        transformations = []
        
        for trans in self.root.findall('.//TRANSFORMATION'):
            trans_info = {
                'name': trans.get('NAME', 'Unknown'),
                'type': trans.get('TYPE', 'Unknown'),
                'description': trans.get('DESCRIPTION', ''),
                'fields': [],
                'conditions': []
            }
            
            for field in trans.findall('.//TRANSFORMFIELD'):
                field_info = {
                    'name': field.get('NAME'),
                    'datatype': field.get('DATATYPE', ''),
                    'expression': field.get('EXPRESSION', ''),
                }
                trans_info['fields'].append(field_info)
            
            for condition in trans.findall('.//FILTERCONDITION'):
                trans_info['conditions'].append(condition.text)
            
            for tableattr in trans.findall('.//TABLEATTRIBUTE'):
                trans_info['table_name'] = tableattr.get('NAME', '')
            
            transformations.append(trans_info)
        
        return transformations
    
    def extract_targets(self) -> List[Dict]:
        """Extract target table definitions"""
        targets = []
        
        for tgt in self.root.findall('.//TARGET'):
            target_info = {
                'name': tgt.get('NAME', 'Unknown'),
                'database': tgt.get('DATABASETYPE', 'Unknown'),
                'fields': []
            }
            
            for field in tgt.findall('.//TARGETFIELD'):
                field_info = {
                    'name': field.get('NAME'),
                    'datatype': field.get('DATATYPE', 'Unknown'),
                    'precision': field.get('PRECISION', ''),
                    'nullable': field.get('NULLABLE', 'true')
                }
                target_info['fields'].append(field_info)
            
            targets.append(target_info)
        
        return targets
    
    def extract_mappings(self) -> Dict:
        """Extract mapping-level information"""
        mapping_info = {
            'name': self.root.get('NAME', 'Unknown'),
            'description': self.root.get('DESCRIPTION', ''),
            'version': self.root.get('VERSIONNUMBER', 'Unknown')
        }
        return mapping_info
    
    def to_markdown(self) -> str:
        """Convert parsed XML to Markdown format"""
        md_output = []
        
        mapping = self.extract_mappings()
        md_output.append(f"# Informatica Mapping: {mapping['name']}")
        md_output.append("")
        md_output.append(f"**Version:** {mapping['version']}")
        if mapping['description']:
            md_output.append(f"**Description:** {mapping['description']}")
        md_output.append("")
        md_output.append("---")
        md_output.append("")
        
        # Sources
        sources = self.extract_sources()
        md_output.append("## SOURCE TABLES")
        md_output.append("")
        
        for src in sources:
            md_output.append(f"### {src['name']}")
            md_output.append(f"- **Database Type:** {src['database']}")
            md_output.append(f"- **Fields:**")
            md_output.append("")
            md_output.append("| Field Name | Data Type | Precision | Scale |")
            md_output.append("|------------|-----------|-----------|-------|")
            
            for field in src['fields']:
                precision = field['precision'] if field['precision'] else '-'
                scale = field['scale'] if field['scale'] else '-'
                md_output.append(f"| {field['name']} | {field['datatype']} | {precision} | {scale} |")
            
            md_output.append("")
        
        # Transformations
        transformations = self.extract_transformations()
        md_output.append("## TRANSFORMATIONS")
        md_output.append("")
        
        for idx, trans in enumerate(transformations, 1):
            md_output.append(f"### Step {idx}: {trans['name']}")
            md_output.append(f"- **Type:** {trans['type']}")
            
            if trans['description']:
                md_output.append(f"- **Description:** {trans['description']}")
            
            if trans['fields']:
                md_output.append("")
                md_output.append("**Fields & Expressions:**")
                md_output.append("")
                md_output.append("| Field Name | Data Type | Expression/Logic |")
                md_output.append("|------------|-----------|------------------|")
                
                for field in trans['fields']:
                    expr = field['expression'] if field['expression'] else 'N/A'
                    dtype = field['datatype'] if field['datatype'] else 'N/A'
                    md_output.append(f"| {field['name']} | {dtype} | `{expr}` |")
            
            if trans['conditions']:
                md_output.append("")
                md_output.append("**Filter Conditions:**")
                for cond in trans['conditions']:
                    md_output.append(f"```sql")
                    md_output.append(cond)
                    md_output.append(f"```")
            
            if 'table_name' in trans and trans['table_name']:
                md_output.append(f"- **Lookup Table:** {trans['table_name']}")
            
            md_output.append("")
        
        # Targets
        targets = self.extract_targets()
        md_output.append("## TARGET TABLES")
        md_output.append("")
        
        for tgt in targets:
            md_output.append(f"### {tgt['name']}")
            md_output.append(f"- **Database Type:** {tgt['database']}")
            md_output.append(f"- **Fields:**")
            md_output.append("")
            md_output.append("| Field Name | Data Type | Precision | Nullable |")
            md_output.append("|------------|-----------|-----------|----------|")
            
            for field in tgt['fields']:
                precision = field['precision'] if field['precision'] else '-'
                nullable = field['nullable']
                md_output.append(f"| {field['name']} | {field['datatype']} | {precision} | {nullable} |")
            
            md_output.append("")
        
        return "\n".join(md_output)


class ClaudeAPIConverter:
    """Use Claude API to convert markdown to BigQuery SQL automatically"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Claude API key
        
        Get your API key from: https://console.anthropic.com/
        Or set environment variable: ANTHROPIC_API_KEY
        """
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
        
        if not self.api_key:
            raise ValueError(
                "Claude API key required! Either:\n"
                "1. Pass api_key parameter, or\n"
                "2. Set ANTHROPIC_API_KEY environment variable\n"
                "Get your key from: https://console.anthropic.com/"
            )
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "Please install the Anthropic library:\n"
                "pip install anthropic"
            )
    
    def convert_to_bigquery(self, markdown_content: str) -> Dict[str, str]:
        """
        Send markdown to Claude API and get back:
        - Lineage mapping
        - BigQuery SQL
        - Python code (optional)
        """
        
        prompt = f"""# Task: Convert Informatica Mapping to BigQuery

You are provided with an Informatica mapping in Markdown format. Your task is to:

1. **Generate a detailed lineage mapping** showing data flow from source to target
2. **Generate equivalent BigQuery SQL code** that replicates the transformation logic

---

## Input: Informatica Mapping (Markdown Format)

{markdown_content}

---

## Required Output:

### Part A: Lineage Mapping

Create a data lineage table with these columns:
- Step Number
- Component Name
- Component Type (Source/Expression/Filter/Join/Aggregator/Lookup/Target)
- Input Fields
- Transformation Logic
- Output Fields

Format as a markdown table.

### Part B: BigQuery Code

Generate production-ready BigQuery SQL that:
1. Uses CTEs (Common Table Expressions) for each transformation step
2. Includes proper data type conversions
3. Handles NULL values appropriately
4. Adds comments explaining each step
5. Follows BigQuery best practices

Output the SQL in executable format that can be run directly in BigQuery.

Wrap the SQL in ```sql code blocks.

---

Please provide both outputs in a clear, structured format with clear section headers.
"""
        
        print("Sending request to Claude API...")
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            
            print("✓ Received response from Claude API")
            
            # Parse the response to extract lineage and SQL
            lineage = self._extract_section(response_text, "Part A", "Part B")
            sql_code = self._extract_sql_blocks(response_text)
            
            return {
                'full_response': response_text,
                'lineage': lineage,
                'sql': sql_code
            }
            
        except Exception as e:
            print(f"✗ Error calling Claude API: {e}")
            raise
    
    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """Extract text between two markers"""
        try:
            start = text.find(start_marker)
            end = text.find(end_marker)
            if start != -1 and end != -1:
                return text[start:end].strip()
            return ""
        except:
            return ""
    
    def _extract_sql_blocks(self, text: str) -> str:
        """Extract SQL code from markdown code blocks"""
        import re
        sql_blocks = re.findall(r'```sql\n(.*?)\n```', text, re.DOTALL)
        return '\n\n'.join(sql_blocks) if sql_blocks else text


def main():
    """Main automation workflow"""
    
    parser = argparse.ArgumentParser(
        description='Automated Informatica to BigQuery Converter'
    )
    parser.add_argument(
        'xml_file',
        help='Path to Informatica XML file'
    )
    parser.add_argument(
        '--api-key',
        help='Claude API key (or set ANTHROPIC_API_KEY env var)',
        default=None
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for generated files',
        default='./output'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("AUTOMATED INFORMATICA TO BIGQUERY CONVERTER")
    print("=" * 80)
    print()
    
    # Step 1: Read XML file
    print(f"[1/5] Reading XML file: {args.xml_file}")
    try:
        with open(args.xml_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        print("✓ XML file loaded")
    except FileNotFoundError:
        print(f"✗ Error: File not found: {args.xml_file}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        sys.exit(1)
    
    print()
    
    # Step 2: Parse and convert to markdown
    print("[2/5] Converting XML to Markdown")
    try:
        parser = InformaticaXMLParser(xml_content)
        markdown = parser.to_markdown()
        print("✓ Markdown generated")
    except Exception as e:
        print(f"✗ Error converting to markdown: {e}")
        sys.exit(1)
    
    print()
    
    # Step 3: Send to Claude API
    print("[3/5] Sending to Claude API for conversion")
    try:
        converter = ClaudeAPIConverter(api_key=args.api_key)
        result = converter.convert_to_bigquery(markdown)
        print("✓ Conversion complete")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    
    print()
    
    # Step 4: Create output directory
    print(f"[4/5] Preparing output directory: {args.output_dir}")
    os.makedirs(args.output_dir, exist_ok=True)
    print("✓ Directory ready")
    
    print()
    
    # Step 5: Save outputs
    print("[5/5] Saving output files")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(args.xml_file))[0]
    
    files_saved = []
    
    # Save markdown
    markdown_file = os.path.join(args.output_dir, f"{base_name}_markdown.md")
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
    files_saved.append(markdown_file)
    
    # Save full response
    response_file = os.path.join(args.output_dir, f"{base_name}_full_response.md")
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write(result['full_response'])
    files_saved.append(response_file)
    
    # Save lineage
    if result['lineage']:
        lineage_file = os.path.join(args.output_dir, f"{base_name}_lineage.md")
        with open(lineage_file, 'w', encoding='utf-8') as f:
            f.write(result['lineage'])
        files_saved.append(lineage_file)
    
    # Save SQL
    if result['sql']:
        sql_file = os.path.join(args.output_dir, f"{base_name}_bigquery.sql")
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(result['sql'])
        files_saved.append(sql_file)
    
    print("✓ Files saved:")
    for file_path in files_saved:
        print(f"  - {file_path}")
    
    print()
    print("=" * 80)
    print("CONVERSION COMPLETE!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Review the generated SQL file")
    print("2. Update table references (project.dataset.table)")
    print("3. Test in BigQuery")
    print("4. Validate results")
    print()
    print(f"SQL file: {sql_file}")
    print()


if __name__ == "__main__":
    main()
