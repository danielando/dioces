"""Azure Function entry points for the Policy Localisation Engine.

Provides two triggers:
  - HTTP trigger (POST /api/localise) for on-demand runs
  - Timer trigger for scheduled annual runs
"""

import json
import logging
import sys
from pathlib import Path

import azure.functions as func

# Add src to path so the policy_localiser package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policy_localiser.config import Config
from policy_localiser.graph.auth import GraphAuth
from policy_localiser.graph.client import GraphClient
from policy_localiser.graph.sharepoint_files import SharePointFiles
from policy_localiser.graph.sharepoint_lists import SharePointLists
from policy_localiser.orchestrator.sharepoint_pipeline import SharePointPipeline

app = func.FunctionApp()


def _build_pipeline() -> SharePointPipeline:
    config = Config.from_env()
    auth = GraphAuth(config.tenant_id, config.client_id, config.client_secret)
    client = GraphClient(auth)
    sp_lists = SharePointLists(client, config.sharepoint_site_id)
    sp_files = SharePointFiles(client, config.sharepoint_site_id)
    return SharePointPipeline(sp_lists, sp_files)


@app.route(route="localise", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def manual_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger for on-demand runs.

    POST body (optional):
    {
        "schools": ["STM", "HFC"],     // filter to specific schools
        "templates": ["Enrolment Policy"]  // filter to specific templates
    }
    """
    logging.info("Manual policy localisation triggered")

    body = {}
    try:
        body = req.get_json()
    except ValueError:
        pass

    school_filter = body.get("schools")
    template_filter = body.get("templates")

    try:
        pipeline = _build_pipeline()
        results = pipeline.run(
            school_filter=school_filter,
            template_filter=template_filter,
        )

        success = sum(1 for r in results if r.status.value == "Success")
        failed = sum(1 for r in results if r.status.value == "Error")

        return func.HttpResponse(
            json.dumps({
                "processed": len(results),
                "success": success,
                "failed": failed,
            }),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logging.exception("Policy localisation failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


# Timer: runs at 2:00 AM on January 15 each year
@app.timer_trigger(
    schedule="0 0 2 15 1 *",
    arg_name="timer",
    run_on_startup=False,
)
def annual_policy_localisation(timer: func.TimerRequest) -> None:
    """Scheduled annual policy localisation run."""
    logging.info("Starting scheduled annual policy localisation")

    try:
        pipeline = _build_pipeline()
        results = pipeline.run()
        success = sum(1 for r in results if r.status.value == "Success")
        failed = sum(1 for r in results if r.status.value == "Error")
        logging.info(
            f"Annual run complete: {success} succeeded, {failed} failed "
            f"out of {len(results)}"
        )
    except Exception:
        logging.exception("Annual policy localisation failed")
        raise
