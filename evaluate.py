import sacrebleu
import logging
import csv
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def read_file(file_path):
    """Read lines from a file and return them as a list."""
    logger.info(f"Reading file: {file_path}")
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    return [line.strip() for line in lines]


def evaluate_translations(prediction_file, reference_file, eval_dataset_name, method):
    """Evaluate translations using BLEU, TER, and CHRF."""
    model_translations = read_file(prediction_file)
    reference_translations = read_file(reference_file)

    # Ensure both files have the same number of lines
    if len(model_translations) != len(reference_translations):
        logger.error(
            "The number of lines in the model and reference files do not match."
        )
        return

    bleu = sacrebleu.corpus_bleu(model_translations, [reference_translations])
    ter = sacrebleu.corpus_ter(model_translations, [reference_translations])
    chrf = sacrebleu.corpus_chrf(model_translations, [reference_translations])

    logger.info(f"BLEU score: {bleu.score:.2f}")
    logger.info(f"TER score: {ter.score:.2f}")
    logger.info(f"CHRF score: {chrf.score:.2f}")

    current_date = datetime.now().strftime("%Y-%m-%d")
    results = {
        "Method": method,
        "Date": current_date,
        "Eval Dataset": eval_dataset_name,
        "BLEU": f"{bleu.score:.2f}",
        "TER": f"{ter.score:.2f}",
        "CHRF": f"{chrf.score:.2f}",
    }

    return results


def write_csv(results, output_file):
    """Append evaluation results to a CSV file, creating it if it doesn't exist."""
    fieldnames = ["Method", "Date", "Eval Dataset", "BLEU", "TER", "CHRF"]

    file_exists = os.path.isfile(output_file)

    mode = "a" if file_exists else "w"
    logger.info(
        f"{'Appending' if file_exists else 'Writing'} results to CSV: {output_file}"
    )

    with open(output_file, mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(results)


if __name__ == "__main__":
    model_file_path = "eval/de-fr.txt/EMEA.de-fr.de_model"
    reference_file_path = "eval/de-fr.txt/EMEA.de-fr.de"
    eval_dataset_name = "EMEA de-fr"
    output_csv_path = "evaluation_results.csv"
    method = "GPT4o-mini"

    results = evaluate_translations(
        model_file_path, reference_file_path, eval_dataset_name
    )
    if results:
        write_csv(results, output_csv_path)
        logger.info(f"Evaluation complete. Results written to {output_csv_path}")
