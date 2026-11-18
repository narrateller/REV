import hashlib
import json

base_path = 'E:/Projects/REV/cad/source/force_geometry/'
files = ['A-V1.FCStd', 'A-V2.FCStd', 'B-V1.FCStd', 'B-V2.FCStd']

print('=== SHA-256 CAD файлов ===')
for fcfile in files:
    with open(base_path + fcfile, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    print(f'{fcfile}: {sha256}')

print()
print('=== manifest.json SHA-256 ===')
with open(base_path + 'manifest.json', 'r', encoding='utf-8') as f:
    manifest = json.load(f)
    
for variant_id, variant_data in manifest['variants'].items():
    print(variant_id + ': ' + variant_data['sha256'])
