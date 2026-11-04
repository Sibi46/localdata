import json
from pathlib import Path
from django.core.management.base import BaseCommand
from jobs.world_geography import import_world_geography


class Command(BaseCommand):
    help = 'Import bundled worldwide states/districts. Defaults to a read-only preview.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Write additions and source links in one transaction.')
        parser.add_argument('--report', help='Optional local JSON report path (writes a file).')

    def handle(self, *args, **options):
        report = import_world_geography(dry_run=not options['apply'])
        if options['report']:
            Path(options['report']).write_text(json.dumps(report, indent=2), encoding='utf-8')
        summary = {k: v for k, v in report.items() if k != 'skipped'}
        summary['skipped_counts'] = {k: len(v) for k, v in report['skipped'].items()}
        self.stdout.write(json.dumps(summary, indent=2))
        self.stdout.write('PREVIEW ONLY: no database changes.' if report['dry_run'] else 'Import committed. Existing geographic assignments preserved.')
