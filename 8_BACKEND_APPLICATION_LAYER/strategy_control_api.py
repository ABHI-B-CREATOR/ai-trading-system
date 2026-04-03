from flask import Blueprint, request, jsonify
from datetime import datetime


class StrategyControlAPI:

    def __init__(self, strategy_registry):

        """
        strategy_registry:
        dict like
        {
            "trend": strategy_obj,
            "breakout": strategy_obj
        }
        """

        self.registry = strategy_registry

        self.blueprint = Blueprint(
            "strategy_control_api",
            __name__,
            url_prefix="/api/strategy"
        )

        self._register_routes()

        print("🎮 Strategy Control API Initialised")

    # -------------------------------------------------

    def _register_routes(self):

        @self.blueprint.route("/list", methods=["GET"])
        def list_strategies():

            data = {
                name: strat.get_status()
                for name, strat in self.registry.items()
            }

            return jsonify(data)

        # ---------------------------------------------

        @self.blueprint.route("/start", methods=["POST"])
        def start_strategy():

            body = request.json
            name = body.get("strategy")

            strat = self.registry.get(name)

            if not strat:
                return jsonify({"error": "strategy not found"}), 404

            strat.start()

            return jsonify({
                "msg": f"{name} started",
                "time": datetime.utcnow().isoformat()
            })

        # ---------------------------------------------

        @self.blueprint.route("/stop", methods=["POST"])
        def stop_strategy():

            body = request.json
            name = body.get("strategy")

            strat = self.registry.get(name)

            if not strat:
                return jsonify({"error": "strategy not found"}), 404

            strat.stop()

            return jsonify({
                "msg": f"{name} stopped",
                "time": datetime.utcnow().isoformat()
            })

        # ---------------------------------------------

        @self.blueprint.route("/update_params", methods=["POST"])
        def update_params():

            body = request.json
            name = body.get("strategy")
            params = body.get("params", {})

            strat = self.registry.get(name)

            if not strat:
                return jsonify({"error": "strategy not found"}), 404

            strat.update_parameters(params)

            return jsonify({
                "msg": f"{name} params updated",
                "params": params,
                "time": datetime.utcnow().isoformat()
            })

        # ---------------------------------------------

        @self.blueprint.route("/emergency_pause", methods=["POST"])
        def emergency_pause():

            for strat in self.registry.values():
                strat.stop()

            return jsonify({
                "msg": "ALL strategies paused",
                "time": datetime.utcnow().isoformat()
            })

    # -------------------------------------------------

    def get_blueprint(self):
        return self.blueprint