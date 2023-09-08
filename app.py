# Proyecto Web simple de calculadora de impuesto a compras con dolares

# Imports

import json
import logging
import os
import sys
from datetime import datetime

import requests
from flask import Flask, jsonify, render_template, request
from flask_caching import Cache

# Logging
format = "[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
    format=format,
    stream=sys.stdout,
)

# Read settings json
conf = {}

try:
    with open(os.path.join(os.path.dirname(__name__), "conf", "settings.json"), "r") as f:
        conf = json.load(f)
except json.JSONDecodeError as err:
    logging.error("Error loading settings.json: " + str(err))
    sys.exit(1)

logging.info("Settings loaded")

# Start
app = Flask(__name__)
cache = Cache(config={"CACHE_TYPE": "simple"})
cache.init_app(app)

logging.info("App started and cache initialized")


# Get current time
@app.route("/get_time", methods=["GET"])
def get_time():
    if request.method == "GET":
        return jsonify({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


# Get dolar from API
@app.route("/get_conversion_usd", methods=["GET"])
@cache.cached(timeout=60 * 10)
def get_conversion_usd():
    logging.info("Updating dollar values")
    if request.method == "GET":
        response = requests.get(conf["dolar_api_html"])
        if response.status_code == 200:
            for tipo_cambio in response.json():
                if tipo_cambio["casa"]["nombre"] == "Dolar Oficial":
                    return jsonify(
                        {
                            "compra": float(tipo_cambio["casa"]["compra"].replace(",", ".")),
                            "venta": float(tipo_cambio["casa"]["venta"].replace(",", ".")),
                            "updated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
        return jsonify({"compra": None, "venta": None})


# Calculate taxes
@app.route("/post_calculate_taxes", methods=["POST"])
def post_calculate_taxes():
    if request.method == "POST":
        # Get form data from user
        data = dict(request.form)
        usd_oficial_venta = data["usd_oficial_venta"]
        # Calculate taxes
        try:
            initial_cost_ars = float(data["cost_product_usd"].replace(",", "."))
            initial_cost_ars = initial_cost_ars * float(usd_oficial_venta)
            cost_ganancias = initial_cost_ars * conf["tax_ganancias"]
            cost_pais = initial_cost_ars * conf["tax_pais"]
            cost_total_ars = initial_cost_ars + cost_ganancias + cost_pais
            # Return results
            return jsonify(
                {
                    "cost_total_ars": round(cost_total_ars, 2),
                    "cost_ganancias": round(cost_ganancias, 2),
                    "subtotal": round(initial_cost_ars, 2),
                    "cost_pais": round(cost_pais, 2),
                    "error_msg": None,
                }
            )
        except BaseException as err:
            # Return error
            logging.error(err)
            return jsonify(
                {
                    "cost_total_ars": None,
                    "cost_ganancias": None,
                    "cost_pais": None,
                    "subtotal": None,
                    "error_msg": "Error al calcular el impuesto, el valor no es un numero",
                    "error_code": str(err),
                }
            )


# Start page
@app.route("/", methods=["GET"])
def view_home():
    return render_template("index.html", interval_seconds=conf["interval_seconds_update"])


# Main
if __name__ == "__main__":
    app.run(port=8000, debug=True, threaded=True)
