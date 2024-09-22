import ast
import sys
from lxml import etree


if __name__ == "__main__":
    filenames = sys.argv[1:]
    translatables = []

    for filename in filenames:
        if filename.endswith('.ui'):
            root = etree.parse(filename).getroot()
            translatable_props = root.findall('.//property[@translatable="yes"]')
            if translatable_props:
                translatables.append(filename)
        elif filename.endswith('.py'):
            source = open(filename, 'r').read()
            for node in ast.iter_child_nodes(ast.parse(source)):
                if isinstance(node, ast.ImportFrom) or isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == '_':
                            translatables.append(filename)
                            continue
        else:
            translatables.append(filename)

    for file in sorted(translatables):
        print(file.removeprefix('../'))
