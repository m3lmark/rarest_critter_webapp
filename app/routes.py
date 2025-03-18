from flask import Blueprint, render_template, request
import requests
import concurrent.futures
import time

bp = Blueprint('main', __name__)

def fetch_with_retries(url, params, max_retries=5, backoff_factor=0.3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                raise e

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        filter_by_species_type = 'filter_by_species_type' in request.form
        species_type = request.form.get('species_type') if filter_by_species_type else None
        number_of_results = int(request.form.get('number_of_results', 5))

        taxon_frequency = {}
        species_counts_url = "https://api.inaturalist.org/v1/observations/species_counts"
        params = {
            "user_id": username,
            "fields": "taxon.name,taxon.rank,taxon.observations_count",
            "per_page": 100,
            "page": 1,
        }

        if filter_by_species_type and species_type:
            params["iconic_taxa"] = species_type

        while True:
            try:
                response = fetch_with_retries(species_counts_url, params)
                data = response.json()
                for result in data["results"]:
                    taxon_id = result["taxon"]["id"]
                    observations_count = result["taxon"]["observations_count"]
                    taxon_type = result["taxon"].get("iconic_taxon_name", "unknown")
                    taxon_frequency[taxon_id] = {
                        "count": observations_count,
                        "type": taxon_type
                    }
                if data["total_results"] <= params["page"] * params["per_page"]:
                    break
                params["page"] += 1
            except requests.exceptions.RequestException as e:
                return render_template('index.html', error=f"Error fetching species counts: {e}")

        if len(taxon_frequency) < number_of_results:
            return render_template('index.html', error="Not enough observations for the limit provided.")

        sorted_taxa = sorted(taxon_frequency.items(), key=lambda item: item[1]["count"])[:number_of_results]

        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_taxon = {
                executor.submit(fetch_taxon_info, taxon_id): taxon_id
                for taxon_id, _ in sorted_taxa
            }
            for future in concurrent.futures.as_completed(future_to_taxon):
                taxon_id = future_to_taxon[future]
                try:
                    taxon_name, image_url = future.result()
                    observations_count = taxon_frequency[taxon_id]["count"]
                    taxon_type = taxon_frequency[taxon_id]["type"]
                    observation_url = f"https://www.inaturalist.org/observations?user_id={username}&taxon_id={taxon_id}"
                    results.append((taxon_name, taxon_id, observations_count, taxon_type, observation_url, image_url))
                except Exception as exc:
                    return render_template('index.html', error=f"Error fetching taxon name for Taxon ID {taxon_id}: {exc}")

        results.sort(key=lambda x: x[2])
        return render_template('index.html', results=results, number_of_results=number_of_results)

    return render_template('index.html')

def fetch_taxon_info(taxon_id):
    taxon_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    response = fetch_with_retries(taxon_url, {})
    if response.status_code == 200:
        taxon_data = response.json()
        if "results" in taxon_data and len(taxon_data["results"]) > 0:
            common_name = taxon_data["results"][0].get("preferred_common_name")
            scientific_name = taxon_data["results"][0].get("name", "Unknown")
            image_url = taxon_data["results"][0].get("default_photo", {}).get("square_url")
            return (common_name if common_name else scientific_name, image_url)
    return (None, None)

# Custom filter to format numbers with commas
@bp.app_template_filter('format_number')
def format_number(value):
    return "{:,}".format(value)