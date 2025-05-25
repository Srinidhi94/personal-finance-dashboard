#!/usr/bin/env python3

import json
import os
import re
import glob
from datetime import datetime
from typing import Dict, List, Optional
import ast
import inspect

class DocUpdater:
    def __init__(self, config_path: str = "docs/ai_reference.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.root_dir = os.path.dirname(os.path.dirname(config_path))

    def update_all(self):
        """Update all documentation based on source code changes"""
        self._update_parsers()
        self._update_api()
        self._update_architecture()
        self._update_config_timestamp()

    def _update_parsers(self):
        """Update parser documentation"""
        parser_mapping = self.config['documentation_structure']['parsers']['source_code_mapping']
        
        for doc_file, source_files in parser_mapping.items():
            doc_path = os.path.join(self.root_dir, 'docs/parsers', doc_file)
            
            # Extract information from source files
            class_info = {}
            test_info = {}
            
            for source_file in source_files:
                if 'test_' in source_file:
                    test_info.update(self._extract_test_info(source_file))
                else:
                    class_info.update(self._extract_class_info(source_file))
            
            # Update documentation
            self._update_parser_doc(doc_path, class_info, test_info)

    def _extract_class_info(self, source_file: str) -> Dict:
        """Extract class information from source file"""
        file_path = os.path.join(self.root_dir, source_file)
        if not os.path.exists(file_path):
            return {}

        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())

        info = {
            'classes': {},
            'functions': {},
            'patterns': {},
            'constants': {}
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                info['classes'][node.name] = {
                    'docstring': ast.get_docstring(node),
                    'methods': self._extract_methods(node)
                }
            elif isinstance(node, ast.FunctionDef):
                info['functions'][node.name] = {
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'returns': self._extract_return_type(node)
                }
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper():  # Constants
                            info['constants'][target.id] = self._extract_value(node.value)

        return info

    def _extract_test_info(self, test_file: str) -> Dict:
        """Extract test information from test file"""
        file_path = os.path.join(self.root_dir, test_file)
        if not os.path.exists(file_path):
            return {}

        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())

        test_info = {
            'test_cases': {},
            'test_data': {}
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_info['test_cases'][node.name] = {
                    'docstring': ast.get_docstring(node),
                    'assertions': self._extract_assertions(node)
                }

        return test_info

    def _update_parser_doc(self, doc_path: str, class_info: Dict, test_info: Dict):
        """Update parser documentation file"""
        if not os.path.exists(doc_path):
            return

        with open(doc_path, 'r') as f:
            content = f.read()

        # Update implementation details
        for class_name, class_data in class_info['classes'].items():
            section_pattern = f"### {class_name}\n```python(.*?)```"
            new_section = self._generate_class_section(class_name, class_data)
            content = re.sub(section_pattern, new_section, content, flags=re.DOTALL)

        # Update test section
        test_section = "## Testing\n```python"
        new_test_section = self._generate_test_section(test_info)
        content = self._replace_section(content, test_section, new_test_section)

        with open(doc_path, 'w') as f:
            f.write(content)

    def _update_api(self):
        """Update API documentation"""
        api_mapping = self.config['documentation_structure']['api']['source_code_mapping']
        
        for doc_file, source_files in api_mapping.items():
            doc_path = os.path.join(self.root_dir, 'docs/api', doc_file)
            
            # Extract API information
            api_info = {}
            for source_file in source_files:
                api_info.update(self._extract_api_info(source_file))
            
            # Update documentation
            self._update_api_doc(doc_path, api_info)

    def _update_architecture(self):
        """Update architecture documentation"""
        arch_mapping = self.config['documentation_structure']['architecture']['source_code_mapping']
        
        for doc_file, source_files in arch_mapping.items():
            doc_path = os.path.join(self.root_dir, 'docs/architecture', doc_file)
            
            # Extract architecture information
            arch_info = {}
            for source_file in source_files:
                arch_info.update(self._extract_architecture_info(source_file))
            
            # Update documentation
            self._update_architecture_doc(doc_path, arch_info)

    def _update_config_timestamp(self):
        """Update the last_updated timestamp in config"""
        self.config['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        with open(os.path.join(self.root_dir, 'docs/ai_reference.json'), 'w') as f:
            json.dump(self.config, f, indent=4)

    @staticmethod
    def _extract_methods(class_node: ast.ClassDef) -> Dict:
        """Extract method information from class node"""
        methods = {}
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                methods[node.name] = {
                    'docstring': ast.get_docstring(node),
                    'args': [arg.arg for arg in node.args.args],
                    'returns': None  # Add return type extraction if needed
                }
        return methods

    @staticmethod
    def _extract_return_type(func_node: ast.FunctionDef) -> Optional[str]:
        """Extract return type annotation from function node"""
        if func_node.returns:
            return ast.unparse(func_node.returns)
        return None

    @staticmethod
    def _extract_value(value_node: ast.AST) -> str:
        """Extract value from AST node"""
        return ast.unparse(value_node)

    @staticmethod
    def _extract_assertions(test_node: ast.FunctionDef) -> List[str]:
        """Extract assertions from test function"""
        assertions = []
        for node in ast.walk(test_node):
            if isinstance(node, ast.Assert):
                assertions.append(ast.unparse(node))
        return assertions

    @staticmethod
    def _generate_class_section(class_name: str, class_data: Dict) -> str:
        """Generate markdown section for a class"""
        methods = class_data['methods']
        docstring = class_data['docstring'] or ""
        
        section = [f"### {class_name}\n```python"]
        section.append(f"class {class_name}:")
        section.append(f'    """{docstring}"""')
        
        for method_name, method_data in methods.items():
            args = ", ".join(method_data['args'])
            docstring = method_data['docstring'] or ""
            section.append(f"\n    def {method_name}({args}):")
            section.append(f'        """{docstring}"""')
            section.append("        pass")
        
        section.append("```\n")
        return "\n".join(section)

    @staticmethod
    def _generate_test_section(test_info: Dict) -> str:
        """Generate markdown section for tests"""
        section = ["## Testing\n```python"]
        
        for test_name, test_data in test_info['test_cases'].items():
            docstring = test_data['docstring'] or ""
            section.append(f"\ndef {test_name}():")
            section.append(f'    """{docstring}"""')
            for assertion in test_data['assertions']:
                section.append(f"    {assertion}")
        
        section.append("```\n")
        return "\n".join(section)

    @staticmethod
    def _replace_section(content: str, section_start: str, new_section: str) -> str:
        """Replace a section in the markdown content"""
        start_idx = content.find(section_start)
        if start_idx == -1:
            return content
        
        end_idx = content.find("```", start_idx + len(section_start))
        if end_idx == -1:
            return content
        
        return content[:start_idx] + new_section + content[end_idx + 3:]

def main():
    updater = DocUpdater()
    updater.update_all()

if __name__ == "__main__":
    main() 