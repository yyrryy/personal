import os

startpath= os.getcwd()
for root, dirs, files in os.walk(startpath):
    if ('pycach' in root or 'migrations' in root):
        pass
    else:
        level = root.replace(startpath, '').count(os.sep)
        indent = ' ' * 4 * (level)
        print('{}{}/'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))