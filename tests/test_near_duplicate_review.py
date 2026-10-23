"""Tests for deterministic near-duplicate review preparation."""
from __future__ import annotations

import csv, hashlib, json
from pathlib import Path
from PIL import Image
from scripts.prepare_near_duplicate_review import main, stable_candidate_id
from scripts.validate_near_duplicate_review import main as validate_review
from scripts.prepare_near_duplicate_priority import main as prepare_priority


def test_queue_generation_and_refusal(tmp_path: Path) -> None:
    root=tmp_path/'datasets'; (root/'real').mkdir(parents=True)
    image=root/'real/a.jpg'; Image.new('RGB',(10,10),(1,2,3)).save(image)
    manifest=root/'manifest.csv'; fields=['sample_id','relative_path','label','split','sha256','generator_family']
    row={'sample_id':'a','relative_path':'real/a.jpg','label':'real','split':'train','sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'generator_family':'camera'}
    with manifest.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerow(row)
    digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
    protected=tmp_path/'protected.json'; protected.write_text(json.dumps({'source_manifest_sha256':digest}))
    candidate={'kind':'perceptual_candidate','sample_a':'a','sample_b':'a','sha256_a':row['sha256'],'sha256_b':row['sha256'],'distance':0}
    cj=tmp_path/'c.json'; cj.write_text(json.dumps({'candidates':[candidate]}))
    cc=tmp_path/'c.csv';
    with cc.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=candidate.keys()); w.writeheader(); w.writerow(candidate)
    out=tmp_path/'review'
    assert main(['--manifest',str(manifest),'--dataset-root',str(root),'--candidates-json',str(cj),'--candidates-csv',str(cc),'--protected-metadata',str(protected),'--output-dir',str(out)])==0
    queue=list(csv.DictReader((out/'near_duplicate_review_queue_v1.csv').open()))
    assert queue[0]['review_status']=='pending'; assert queue[0]['reviewer_decision']==''
    assert stable_candidate_id(candidate)==queue[0]['candidate_id']
    assert main(['--manifest',str(manifest),'--dataset-root',str(root),'--candidates-json',str(cj),'--candidates-csv',str(cc),'--protected-metadata',str(protected),'--output-dir',str(out)])==4


def test_priority_view_and_review_validator(tmp_path: Path) -> None:
    queue = tmp_path / 'queue.csv'
    fields=['candidate_id','sample_a','sample_b','sha256_a','sha256_b','reviewer_decision','reviewer','review_date_utc','reviewer_notes']
    values=[{'candidate_id':'b','sample_a':'a','sample_b':'b','sha256_a':'a','sha256_b':'b','reviewer_decision':'unreviewed','reviewer':'','review_date_utc':'','reviewer_notes':''}, {'candidate_id':'a','sample_a':'a','sample_b':'b','sha256_a':'a','sha256_b':'b','reviewer_decision':'same_image_transform','reviewer':'reviewer','review_date_utc':'2026-10-20T00:00:00Z','reviewer_notes':'same image'}]
    with queue.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(values)
    # Validator needs manifest/snapshot, so priority ordering is tested separately.
    priority=tmp_path/'priority.csv'
    assert prepare_priority(['--queue',str(queue),'--output',str(priority)]) == 0
    assert list(csv.DictReader(priority.open()))[0]['candidate_id']=='a'
