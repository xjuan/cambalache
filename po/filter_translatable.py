import ast
import sys
from lxml import etree


if __name__ == "__main__":
    filenames = sys.argv[1:]
    translatables = set()

    for filename in filenames:
        if filename.endswith('.ui'):
            root = etree.parse(filename).getroot()
            translatable_attrs = root.findall('.//*[@translatable="yes"]')
            if translatable_attrs:
                translatables.add(filename)
        elif filename.endswith('.py'):
            source = open(filename, 'r').read()
            for node in ast.iter_child_nodes(ast.parse(source)):
                if isinstance(node, ast.ImportFrom) or isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ['_', 'N_']:
                            translatables.add(filename)
                            continue
        else:
            translatables.add(filename)

    for file in sorted(list(translatables)):
        print(file.removeprefix('../'))
