import os
import os.path
import sys

if __name__ == '__main__':
    suffices = sys.argv[2].split(' ')
    dir = sys.argv[1]
    
    count = 0
    for root, dirs, files in os.walk(dir):
        for file in files:
            if os.path.islink(os.path.join(root, file)):
                continue

            if file.split('.')[-1] in suffices:
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        count += len(f.readlines())
                except:
                    pass
    print(count)
