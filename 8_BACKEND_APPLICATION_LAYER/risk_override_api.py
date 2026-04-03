from flask import Blueprint, request, jsonify
from datetime import datetime


class RiskOverrideAPI:

    def __init__(self, risk_engine):

        """
        risk_engine:
        central risk manager object
        expected methods:

        force_square_off()
        reduce_exposure(percent)
        set_risk_mode(mode)
        get_risk_status()
        """

        self.risk_engine = risk_engine

        self.blueprint = Blueprint(
            "risk_override_api",
            __name__,
            url_prefix="/api/risk"
        )

        self._register_routes()

        print("🛑 Risk Override API Initialised")

    # -------------------------------------------------

    def _register_routes(self):

        @self.blueprint.route("/status", methods=["GET"])
        def risk_status():

            status = self.risk_engine.get_risk_status()

            return jsonify(status)

        # -------------------------------------------------

        @self.blueprint.route("/square_off", methods=["POST"])
        def square_off():

            self.risk_engine.force_square_off()

            return jsonify({
                "msg": "All positions square-off triggered",
                "time": datetime.utcnow().isoformat()
            })

        # -------------------------------------------------

        @self.blueprint.route("/reduce_exposure", methods=["POST"])
        def reduce_exposure():

            body = request.json
            percent = body.get("percent", 50)

            self.risk_engine.reduce_exposure(percent)

            return jsonify({
                "msg": f"Exposure reduced by {percent}%",
                "time": datetime.utcnow().isoformat()
            })

        # -------------------------------------------------

        @self.blueprint.route("/set_mode", methods=["POST"])
        def set_mode():

            body = request.json
            mode = body.get("mode", "normal")

            self.risk_engine.set_risk_mode(mode)

            return jsonify({
                "msg": f"Risk mode set to {mode}",
                "time": datetime.utcnow().isoformat()
            })

    # -------------------------------------------------

    def get_blueprint(self):
        return self.blueprint