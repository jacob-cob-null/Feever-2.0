import argparse
import json
import logging
import os
import sys

# Ensure src can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.medical_services_digitizer import BatchProcessor

logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process benchmark raw folders sequentially and generate per-folder SQL files."
    )
    parser.add_argument(
        "--raw-root",
        default="./Benchmark_Data/Raw",
        help="Root directory that contains one folder per source/hospital.",
    )
    parser.add_argument(
        "--sql-dir",
        default="./Benchmark_Data/SQL",
        help="Directory where generated SQL files will be written.",
    )
    parser.add_argument(
        "--output-db",
        default="./data/medical_services.db",
        help="SQLite DB used by the extraction pipeline.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=1,
        help="Starting global service_ID value.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    db_dir = os.path.dirname(args.output_db)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    processor = BatchProcessor(images_dir=args.raw_root, output_db=args.output_db)
    result = processor.process_raw_directories_to_sql(
        raw_root_dir=args.raw_root,
        sql_output_dir=args.sql_dir,
        start_service_id=args.start_id,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
