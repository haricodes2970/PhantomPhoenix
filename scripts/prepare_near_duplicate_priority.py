"""Create a non-destructive deterministic priority view for candidate review."""
from __future__ import annotations
import argparse, csv
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue',type=Path,default=Path('datasets/provenance/near_duplicate_review_v1/near_duplicate_review_queue_v1.csv'))
    parser.add_argument('--output',type=Path,default=Path('datasets/provenance/near_duplicate_review_v1/review_priority_v1.csv'))
    args=parser.parse_args(argv)
    if args.output.exists():
        print(f'refusing to overwrite existing output: {args.output}'); return 4
    rows=list(csv.DictReader(args.queue.open(encoding='utf-8',newline='')))
    for row in rows:
        cross=row.get('cross_split')=='true'; unassigned=row.get('unassigned_involvement')=='true'
        # Review order: assigned cross-split first, then assigned/unassigned, then remaining;
        # within tier, smallest dHash distance first, then stable candidate ID.
        tier=0 if cross and not unassigned else 1 if unassigned else 2
        row['review_priority_tier']=str(tier)
        row['review_priority_reason']=(
            'assigned cross-split candidate' if tier==0 else
            'assigned/unassigned candidate' if tier==1 else
            'remaining candidate'
        )
    rows.sort(key=lambda r:(int(r['review_priority_tier']),int(r.get('distance') or 99),r['candidate_id']))
    fields=list(rows[0]) if rows else []
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,lineterminator='\n'); writer.writeheader(); writer.writerows(rows)
    print(f'created priority view with {len(rows)} candidates')
    return 0

if __name__=='__main__': raise SystemExit(main())
