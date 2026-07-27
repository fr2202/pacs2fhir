"""
LOINC and DICOM modality mappings for CHULN exam types.
LOINC codes for radiology: https://loinc.org/radiology/
DICOM modality codes: http://dicom.nema.org/medical/dicom/current/output/chtml/part16/sect_CID_29.html
"""

EXAM_TYPE_TO_LOINC = {
    # Ultrasound (Ecografia)
    "ecografia articular punho": {"code": "24769-2", "display": "US Joint Wrist", "modality": "US"},
    "ecografia articular punho - bilateral": {"code": "24769-2", "display": "US Joint Wrist bilateral", "modality": "US"},
    "ecografia das glândulas salivares": {"code": "24600-9", "display": "US Salivary gland", "modality": "US"},
    "ecografia renal": {"code": "24683-5", "display": "US Kidney", "modality": "US"},
    "ecografia abdominal": {"code": "24558-9", "display": "US Abdomen", "modality": "US"},
    "ecografia pélvica": {"code": "24604-1", "display": "US Pelvis", "modality": "US"},
    "ecografia tiroideia": {"code": "24627-2", "display": "US Thyroid", "modality": "US"},
    "ecografia cervical": {"code": "24563-9", "display": "US Neck", "modality": "US"},
    "ecografia mamária": {"code": "24602-5", "display": "US Breast", "modality": "US"},
    "ecografia escrotal": {"code": "24611-6", "display": "US Scrotum and testicle", "modality": "US"},
    "ecografia de partes moles": {"code": "24600-9", "display": "US Soft tissue", "modality": "US"},
    "ecografia músculo-tendinosa": {"code": "24769-2", "display": "US Musculoskeletal", "modality": "US"},
    "ecografia hepática": {"code": "24693-4", "display": "US Liver", "modality": "US"},
    "eco-doppler": {"code": "24634-8", "display": "US Doppler", "modality": "US"},
    "eco-doppler venoso": {"code": "24634-8", "display": "US Doppler Veins", "modality": "US"},
    "eco-doppler arterial": {"code": "24634-8", "display": "US Doppler Arteries", "modality": "US"},
    # Fibroscan
    "elastografia hepática - fibroscan": {"code": "36554-4", "display": "US Liver elastography", "modality": "US"},
    "elastografia hepática": {"code": "36554-4", "display": "US Liver elastography", "modality": "US"},
    # CT (Tomografia Computadorizada)
    "tc do tórax": {"code": "24627-2", "display": "CT Chest", "modality": "CT"},
    "tc do tórax com contraste": {"code": "36643-5", "display": "CT Chest with contrast", "modality": "CT"},
    "tc abdominal": {"code": "24558-9", "display": "CT Abdomen", "modality": "CT"},
    "tc abdominal e pélvica": {"code": "24558-9", "display": "CT Abdomen and Pelvis", "modality": "CT"},
    "tc crânio-encefálica": {"code": "25056-5", "display": "CT Head", "modality": "CT"},
    "tc do crânio": {"code": "25056-5", "display": "CT Head", "modality": "CT"},
    "tc de coluna": {"code": "24644-7", "display": "CT Spine", "modality": "CT"},
    "tc pélvica": {"code": "24604-1", "display": "CT Pelvis", "modality": "CT"},
    "tc de tórax e abdómen": {"code": "24627-2", "display": "CT Chest and Abdomen", "modality": "CT"},
    "angio-tc": {"code": "36643-5", "display": "CTA", "modality": "CT"},
    "angio-tc pulmonar": {"code": "24627-2", "display": "CTA Pulmonary Arteries", "modality": "CT"},
    # MRI (Ressonância Magnética)
    "ressonância magnética": {"code": "36643-5", "display": "MR Brain", "modality": "MR"},
    "rm crânio-encefálica": {"code": "36643-5", "display": "MR Head", "modality": "MR"},
    "rm do crânio": {"code": "36643-5", "display": "MR Head", "modality": "MR"},
    "rm do encéfalo": {"code": "36643-5", "display": "MR Brain", "modality": "MR"},
    "rm de coluna": {"code": "36616-1", "display": "MR Spine", "modality": "MR"},
    "rm de coluna lombar": {"code": "36616-1", "display": "MR Lumbar spine", "modality": "MR"},
    "rm de coluna lombossagrada": {"code": "36616-1", "display": "MR Lumbosacral spine", "modality": "MR"},
    "rm de coluna cervical": {"code": "36616-1", "display": "MR Cervical spine", "modality": "MR"},
    "rm de coluna dorsal": {"code": "36616-1", "display": "MR Thoracic spine", "modality": "MR"},
    "rm articular": {"code": "36643-5", "display": "MR Joint", "modality": "MR"},
    "rm hepática": {"code": "36643-5", "display": "MR Liver", "modality": "MR"},
    "rm pélvica": {"code": "36643-5", "display": "MR Pelvis", "modality": "MR"},
    "rm cardíaca": {"code": "36643-5", "display": "MR Heart", "modality": "MR"},
    "angio-rm": {"code": "36643-5", "display": "MRA", "modality": "MR"},
    "imag neuro - rm": {"code": "36643-5", "display": "MR Neuro", "modality": "MR"},
    # Retinography
    "retinografia": {"code": "57127-9", "display": "Retinal photography", "modality": "OP"},
    # X-Ray
    "radiografia": {"code": "24748-6", "display": "XR", "modality": "CR"},
    "radiografia do tórax": {"code": "24748-6", "display": "XR Chest", "modality": "CR"},
    "rx": {"code": "24748-6", "display": "XR", "modality": "CR"},
    # Densitometry
    "densitometria óssea": {"code": "38263-0", "display": "DXA Bone density", "modality": "OT"},
    # Echocardiography
    "ecocardiograma transtorácico": {"code": "34552-0", "display": "Echo transthoracic", "modality": "US"},
    "ecocardiograma transesofágico": {"code": "34553-8", "display": "Echo transesophageal", "modality": "US"},
    "ecocardiograma de stress": {"code": "34544-7", "display": "Echo stress", "modality": "US"},
    "ecocardiograma": {"code": "34552-0", "display": "Echo", "modality": "US"},
    # Angiography / Interventional radiology
    "arteriografia": {"code": "24575-3", "display": "Angiography", "modality": "XA"},
    "arteriografia seletiva": {"code": "24575-3", "display": "Selective angiography", "modality": "XA"},
    "angioplastia": {"code": "59776-5", "display": "Procedure note - angioplasty", "modality": "XA"},
    "angioplastia seletiva": {"code": "59776-5", "display": "Procedure note - selective angioplasty", "modality": "XA"},
    "embolização": {"code": "59776-5", "display": "Procedure note - embolization", "modality": "XA"},
    "embolização arterial": {"code": "59776-5", "display": "Procedure note - arterial embolization", "modality": "XA"},
    "acesso vascular": {"code": "59776-5", "display": "Procedure note - vascular access", "modality": "XA"},
    # Nuclear medicine / Scintigraphy
    "cintigrafia": {"code": "24614-0", "display": "NM study", "modality": "NM"},
    "pet": {"code": "44136-0", "display": "PET scan", "modality": "PT"},
    "spect": {"code": "24614-0", "display": "SPECT study", "modality": "NM"},
    # Mammography / Tomosynthesis
    "mamografia": {"code": "24606-6", "display": "Mammography", "modality": "MG"},
    "tomossíntese": {"code": "36643-5", "display": "Digital breast tomosynthesis", "modality": "MG"},
    # Fluoroscopy / Contrast studies
    "trânsito esofágico": {"code": "24617-3", "display": "XR Esophagus", "modality": "RF"},
    "trânsito gastroduodenal": {"code": "24617-3", "display": "XR Upper GI", "modality": "RF"},
    "enema opaco": {"code": "24604-1", "display": "XR Colon barium enema", "modality": "RF"},
    "urografia": {"code": "24683-5", "display": "XR Urogram", "modality": "RF"},
    "mielografia": {"code": "24644-7", "display": "XR Myelography", "modality": "RF"},
    # Electrophysiology
    "electromiografia": {"code": "28554-8", "display": "EMG study", "modality": "OT"},
    "estudo electromiográfico": {"code": "28554-8", "display": "EMG study", "modality": "OT"},
    "electroencefalograma": {"code": "29749-3", "display": "EEG study", "modality": "OT"},
    # Endoscopy (sometimes in PACS)
    "colonoscopia": {"code": "28023-4", "display": "Colonoscopy report", "modality": "ES"},
    "gastroscopia": {"code": "18751-8", "display": "Upper GI endoscopy report", "modality": "ES"},
    # CT variants
    "tc do tórax com alta resolução": {"code": "24627-2", "display": "CT Chest high resolution", "modality": "CT"},
    "tc cardíaca": {"code": "79060-5", "display": "CT Heart", "modality": "CT"},
    "tc cardíaca (angio-tc)": {"code": "79060-5", "display": "CTA Heart", "modality": "CT"},
    "angio-tc pulmonar": {"code": "24627-2", "display": "CTA Pulmonary", "modality": "CT"},
    "tc do pescoço": {"code": "24563-9", "display": "CT Neck", "modality": "CT"},
    "tc dos membros": {"code": "24627-2", "display": "CT Extremity", "modality": "CT"},
    # MRI variants
    "rm do abdómen": {"code": "36643-5", "display": "MR Abdomen", "modality": "MR"},
    "rm do abdómen superior": {"code": "36643-5", "display": "MR Abdomen upper", "modality": "MR"},
    "rm do pescoço": {"code": "36643-5", "display": "MR Neck", "modality": "MR"},
    "rm do joelho": {"code": "36643-5", "display": "MR Knee", "modality": "MR"},
    "rm do ombro": {"code": "36643-5", "display": "MR Shoulder", "modality": "MR"},
    "rm da mama": {"code": "26349-5", "display": "MR Breast", "modality": "MR"},
    "rm do crânio": {"code": "36643-5", "display": "MR Head", "modality": "MR"},
}

DEFAULT_LOINC = {"code": "18748-4", "display": "Diagnostic imaging study", "modality": "OT"}


def get_loinc_for_exam(exam_type: str) -> dict:
    """Returns LOINC info for a given exam type, using fuzzy prefix matching."""
    normalized = exam_type.lower().strip()
    if normalized in EXAM_TYPE_TO_LOINC:
        return EXAM_TYPE_TO_LOINC[normalized]
    for key, val in EXAM_TYPE_TO_LOINC.items():
        if normalized.startswith(key) or key in normalized:
            return val
    return DEFAULT_LOINC


DICOM_MODALITY_SYSTEM = "http://dicom.nema.org/resources/ontology/DCM"
LOINC_SYSTEM = "http://loinc.org"

SNOMED_IMAGING_PROCEDURE = "363679005"
SNOMED_SYSTEM = "http://snomed.info/sct"
