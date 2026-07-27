import json, base64, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

idx = json.loads(Path('logs/files_with_conclusion.json').read_text(encoding='utf-8'))
idx_sorted = sorted(idx, key=lambda x: x['conclusion_chars'], reverse=True)

# Elegir uno con conclusion larga y status final
target = next(r for r in idx_sorted if r['status'] == 'final' and r['conclusion_chars'] > 500)

print('=' * 70)
print('ARCHIVO FUENTE:', target['file'])
print('EXAMEN        :', target['exam'])
print('STATUS        :', target['status'])
print('CHARS CONCL.  :', target['conclusion_chars'])
print('=' * 70)

bundle_path = Path('output/fhir_con_conclusion') / target['file']
bundle = json.loads(bundle_path.read_text(encoding='utf-8'))

# --- Imprimir estructura del bundle ---
print('\n[BUNDLE]')
print('  resourceType :', bundle['resourceType'])
print('  id           :', bundle['id'])
print('  type         :', bundle['type'])
print('  num entries  :', len(bundle['entry']))

for i, entry in enumerate(bundle['entry']):
    res = entry['resource']
    rt = res['resourceType']
    print(f'\n--- entry[{i}] : {rt} ---')

    if rt == 'Organization':
        print('  id   :', res['id'])
        print('  name :', res['name'])

    elif rt == 'Patient':
        print('  id        :', res['id'])
        print('  birthDate :', res.get('birthDate'))
        print('  identifier:', res['identifier'][0]['system'], '|', res['identifier'][0]['value'])
        print('  managing  :', res.get('managingOrganization', {}).get('reference'))

    elif rt == 'Encounter':
        print('  id      :', res['id'])
        print('  status  :', res['status'])
        print('  class   :', res['class']['code'], '-', res['class']['display'])
        print('  episodio:', res['identifier'][0]['value'])
        print('  subject :', res['subject']['reference'])
        print('  period  :', res.get('period', {}).get('start'))
        if res.get('location'):
            print('  location:', res['location'][0]['location']['display'])

    elif rt == 'ImagingStudy':
        print('  id          :', res['id'])
        print('  status      :', res['status'])
        print('  modality    :', res['modality'][0]['code'])
        print('  accession   :', res['identifier'][0]['value'])
        print('  description :', res.get('description'))
        print('  subject     :', res['subject']['reference'])
        print('  encounter   :', res.get('encounter', {}).get('reference'))
        print('  started     :', res.get('started'))
        loinc = res['reasonCode'][0]['coding'][0]
        print('  LOINC       :', loinc['code'], '-', loinc['display'])

    elif rt == 'DiagnosticReport':
        print('  id          :', res['id'])
        print('  status      :', res['status'])
        cat = res['category'][0]['coding'][0]
        print('  category    :', cat['code'], '-', cat['display'])
        code = res['code']['coding'][0]
        print('  code (LOINC):', code['code'], '-', code['display'])
        print('  code text   :', res['code']['text'])
        print('  subject     :', res['subject']['reference'])
        print('  encounter   :', res.get('encounter', {}).get('reference'))
        print('  imagingStudy:', res['imagingStudy'][0]['reference'])
        print('  effective   :', res.get('effectiveDateTime'))
        print('  issued      :', res.get('issued'))
        pf = res.get('presentedForm', [])
        if pf:
            decoded = base64.b64decode(pf[0]['data']).decode('utf-8', errors='replace')
            print('  presentedForm contentType:', pf[0]['contentType'])
            print('  presentedForm language   :', pf[0]['language'])
            print('  presentedForm title      :', pf[0]['title'])
            print('  presentedForm (decoded)  :')
            for line in decoded[:1200].split('\n'):
                print('    |', line)
        conc = res.get('conclusion', '')
        print(f'\n  conclusion ({len(conc)} chars):')
        for line in conc[:800].split('\n'):
            print('    >', line)

    print('  request.method :', entry['request']['method'])
    print('  request.url    :', entry['request']['url'])
