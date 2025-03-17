from flask import Blueprint, render_template, request
import requests
import concurrent.futures

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        filter_by_species_type = 'filter_by_species_type' in request.form
        species_type = request.form.get('species_type') if filter_by_species_type else 'all species'
        number_of_results = int(request.form.get('number_of_results', 5))

        taxon_frequency = {}
        species_counts_url = "https://api.inaturalist.org/v1/observations/species_counts"
        params = {
            "user_id": username,
            "fields": "taxon.name,taxon.rank,taxon.observations_count",
            "per_page": 100,
            "page": 1,
        }

        if filter_by_species_type and species_type != 'all species':
            params["iconic_taxa"] = species_type

        while True:
            response = requests.get(species_counts_url, params=params)
            if response.status_code == 200:
                data = response.json()
                for result in data["results"]:
                    taxon_id = result["taxon"]["id"]
                    observations_count = result["taxon"]["observations_count"]
                    taxon_frequency[taxon_id] = observations_count
                if data["total_results"] <= params["page"] * params["per_page"]:
                    break
                params["page"] += 1
            else:
                return render_template('index.html', error=f"Error fetching species counts: {response.status_code}")

        sorted_taxa = sorted(taxon_frequency.items(), key=lambda item: item[1])[:number_of_results]

        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_taxon = {
                executor.submit(fetch_taxon_info, taxon_id): taxon_id
                for taxon_id, _ in sorted_taxa
            }
            for future in concurrent.futures.as_completed(future_to_taxon):
                taxon_id = future_to_taxon[future]
                try:
                    taxon_name = future.result()
                    observations_count = taxon_frequency[taxon_id]
                    results.append((taxon_name, taxon_id, observations_count))
                except Exception as exc:
                    return render_template('index.html', error=f"Error fetching taxon name for Taxon ID {taxon_id}: {exc}")

        results.sort(key=lambda x: x[2])
        return render_template('index.html', results=results, number_of_results=number_of_results, species_type=species_type)

    return render_template('index.html')

def fetch_taxon_info(taxon_id):
    taxon_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    response = requests.get(taxon_url)
    if response.status_code == 200:
        taxon_data = response.json()
        if "results" in taxon_data and len(taxon_data["results"]) > 0:
            common_name = taxon_data["results"][0].get("preferred_common_name")
            scientific_name = taxon_data["results"][0].get("name", "Unknown")
            return common_name if common_name else scientific_name
    return None