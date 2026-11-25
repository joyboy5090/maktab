"""
Markazlashtirilgan logging konfiguratsiyasi (Maktab SMS)
Formatlangan JSON yoki standart loglarni chiqarish.
"""
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Keraksiz shovqin loglarni cheklash
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("maktab_sms")
