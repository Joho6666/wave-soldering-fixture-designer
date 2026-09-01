"""ProcessProfile parameter catalog for the dynamic frontend panel."""
from fastapi import APIRouter

from app.services.rules.process_profile import ProcessProfile, parameter_catalog

router = APIRouter(prefix="/process-profile", tags=["process-profile"])


@router.get("")
def get_process_profile():
    catalog = parameter_catalog()
    catalog["current"] = ProcessProfile().to_dict()
    return catalog
