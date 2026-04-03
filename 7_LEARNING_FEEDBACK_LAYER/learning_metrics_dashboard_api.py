from flask import Blueprint, jsonify


class LearningMetricsAPI:

    def __init__(self,
                 performance_analyzer,
                 retraining_scheduler,
                 reinforcement_agent):

        self.performance_analyzer = performance_analyzer
        self.retraining_scheduler = retraining_scheduler
        self.reinforcement_agent = reinforcement_agent

        self.blueprint = Blueprint(
            "learning_metrics_api",
            __name__,
            url_prefix="/api/learning"
        )

        self._register_routes()

    # ---------- ROUTES ----------
    def _register_routes(self):

        @self.blueprint.route("/performance", methods=["GET"])
        def performance_snapshot():
            return jsonify(
                self.performance_analyzer.performance_snapshot()
            )

        @self.blueprint.route("/strategy-summary", methods=["GET"])
        def strategy_summary():
            return jsonify(
                self.performance_analyzer.strategy_summary()
            )

        @self.blueprint.route("/scheduler-status", methods=["GET"])
        def scheduler_status():
            return jsonify(
                self.retraining_scheduler.scheduler_status()
            )

        @self.blueprint.route("/rl-stats", methods=["GET"])
        def rl_stats():
            q_table_size = len(self.reinforcement_agent.q_table)

            return jsonify({
                "q_table_states": q_table_size
            })

    # ---------- GET BLUEPRINT ----------
    def get_blueprint(self):
        return self.blueprint