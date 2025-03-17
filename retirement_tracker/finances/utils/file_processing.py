
from pypdf import PdfReader


def process_user_work_file(user_work_file):
    """ Reads in a user pay stub.
        Processes:
            earnings,
            deductions, and
            taxes.
        Returns a dictionary with the information, which can then be fed into another view. """

    pdf_obj = PdfReader(user_work_file)
    page = pdf_obj.pages[0]
    split_page = page.extract_text().split('\n')

    # Earnings

    # Deductions

    # Taxes
    pass
