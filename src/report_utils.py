import os
import datetime
from PyQt5.QtWidgets import QMessageBox

def show_upload_report(successful_orders, failed_orders, skipped_orders):
    report_message = "Upload Report:\n\n"

    if successful_orders:
        report_message += "Successfully uploaded orders:\n"
        report_message += "\n".join([str(order) for order in successful_orders]) + "\n\n"

    if failed_orders:
        report_message += "Failed to upload orders:\n"
        for failed in failed_orders:
            codice_articolo = failed.get("codiceArticolo", "Unknown")
            report_message += (
                f"Order ID: {failed['ordineId']}, "
                f"Codice Articolo: {codice_articolo}, "
                f"Reason: {failed['reason']}\n"
            )

    if skipped_orders:
        report_message += "Skipped orders (already in database):\n"
        report_message += "\n".join(skipped_orders) + "\n\n"

    QMessageBox.information(None, "Upload Report", report_message)
    save_report_to_file(report_message, "orders")


def save_report_to_file(report_content, report_type):
    if not os.path.exists("./reports"):
        os.makedirs("./reports")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{report_type}_report_{timestamp}.txt"
    file_path = os.path.join("reports", filename)

    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(report_content)
        print(f"Report saved to {file_path}")
    except Exception as e:
        print(f"Failed to save report: {e}")

def show_family_upload_report(successful_families, failed_families, skipped_families):
    report_message = "Upload Report:\n\n"

    if successful_families:
        report_message += "Successfully uploaded Families:\n"
        report_message += "\n".join([str(family) for family in successful_families]) + "\n\n"

    if failed_families:
        report_message += "Failed to upload Families:\n"
        for failed in failed_families:
            report_message += (
                f"Famiglia: {failed['Family']}, Reason: {failed['Reason']}\n"
            )

    if skipped_families:
        report_message += "Skipped families (already in database):\n"
        report_message += "\n".join(skipped_families) + "\n\n"

    QMessageBox.information(None, "Upload Report", report_message)
    save_report_to_file(report_message, "families")
