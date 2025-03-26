from flask import Blueprint, render_template, request
import requests
import concurrent.futures
import time
import logging

bp = Blueprint('main', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PHOTO_URL = "https://png.pngtree.com/png-vector/20221125/ourmid/pngtree-no-image-available-icon-flatvector-illustration-pic-design-profile-vector-png-image_40966566.jpg"

def fetch_with_retries(url, params=None, max_retries=5, backoff_factor=0.3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            if response.status_code == 422:
                return response  # Return the response to handle 422 status code
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                logger.error(f"Failed to fetch data from {url} after {max_retries} attempts")
                raise e

def fetch_taxon_info(taxon_id, max_retries=5, backoff_factor=0.3):
    taxon_url = f"https://api.inaturalist.org/v1/taxa/{taxon_id}"
    for attempt in range(max_retries):
        try:
            response = requests.get(taxon_url)
            if response.status_code == 429:
                time.sleep(backoff_factor * (2 ** attempt))
                continue
            response.raise_for_status()
            taxon_data = response.json()
            logger.info(f"Checking condition: taxon_data={bool(taxon_data)}\n'results' in taxon_data={'results' in taxon_data}\nlen(taxon_data['results'])={len(taxon_data['results']) if 'results' in taxon_data else 'N/A'}")
            if taxon_data and "results" in taxon_data and len(taxon_data["results"]) > 0:
                taxon_result = taxon_data["results"][0]
                common_name = taxon_result.get("preferred_common_name")
                scientific_name = taxon_result.get("name", "Unknown")
                image_url = taxon_result.get("default_photo", {}).get("square_url", DEFAULT_PHOTO_URL) if taxon_result.get("default_photo") else DEFAULT_PHOTO_URL
                logger.info(f"Fetched taxon info for Taxon ID {taxon_id}: common_name={common_name}, scientific_name={scientific_name}, image_url={image_url}")
                return (common_name if common_name else scientific_name, image_url)
            logger.error(f"No results found in taxon data for Taxon ID {taxon_id}: {taxon_data}")
            return (None, DEFAULT_PHOTO_URL)
        except requests.exceptions.RequestException as e:
            logger.error(f"RequestException while fetching taxon info for Taxon ID {taxon_id} on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(backoff_factor * (2 ** attempt))
            else:
                logger.error(f"Failed to fetch taxon info for Taxon ID {taxon_id} after {max_retries} attempts")
                raise e
    return (None, DEFAULT_PHOTO_URL)

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form.get('username')
        filter_by_species_type = 'filter_by_species_type' in request.form
        species_type = request.form.get('species_type') if filter_by_species_type else None
        number_of_results = int(request.form.get('number_of_results', 5))
        filter_by_research_grade = 'filter_by_research_grade' in request.form
        research_grade = request.form.get('research_grade') if filter_by_research_grade else None

        taxon_frequency = {}
        species_counts_url = "https://api.inaturalist.org/v1/observations/species_counts"
        params = {
            "user_id": username,
            "fields": "taxon.name,taxon.rank,taxon.observations_count",
            "per_page": 100,
            "page": 1,
            "quality_grade": "any"  # Include both verified and unverified observations by default
        }

        if filter_by_species_type and species_type:
            params["iconic_taxa"] = species_type

        if filter_by_research_grade and research_grade:
            params["quality_grade"] = research_grade

        total_observations = 0
        while True:
            try:
                response = fetch_with_retries(species_counts_url, params)
                if response.status_code == 422:
                    return render_template('index.html', error=f"The username '{username}' does not exist. Please enter a valid iNaturalist username.")
                data = response.json()
                for result in data["results"]:
                    taxon_id = result["taxon"]["id"]
                    observations_count = result["taxon"]["observations_count"]
                    taxon_type = result["taxon"].get("iconic_taxon_name", "unknown")
                    taxon_frequency[taxon_id] = {
                        "count": observations_count,
                        "type": taxon_type,
                        "quality_grade": research_grade if filter_by_research_grade else "any"
                    }
                    total_observations += observations_count
                if data["total_results"] <= params["page"] * params["per_page"]:
                    break
                params["page"] += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching species counts for user {username} on page {params['page']}: {e}")
                return render_template('index.html', error=f"Error fetching species counts: {e}")

        if len(taxon_frequency) < number_of_results:
            error_message = ""
            if research_grade:
                if len(taxon_frequency) == 0:
                    error_message = f"{username} does not have any {research_grade} observations."
                if species_type:
                    if len(taxon_frequency) == 1:
                        error_message = f"{username} only has {len(taxon_frequency)} {research_grade} {species_type} observation which is not sufficient for the number requested."
                    else:
                        error_message = f"{username} only has {len(taxon_frequency)} {research_grade} {species_type} observations which is not sufficient for the number requested."
                else:
                    if len(taxon_frequency) == 1:
                        error_message = f"{username} only has {len(taxon_frequency)} {research_grade} observation which is not sufficient for the number requested."
                    else:
                        error_message = f"{username} only has {len(taxon_frequency)} {research_grade} observations which is not sufficient for the number requested."
            else:
                if len(taxon_frequency) == 0:
                    error_message = f"{username} does not have any observations."
                if species_type:
                    if len(taxon_frequency) == 1:
                        error_message = f"{username} only has {len(taxon_frequency)} {species_type} observation which is not sufficient for the number requested."
                    else:
                        error_message = f"{username} only has {len(taxon_frequency)} {species_type} observations which is not sufficient for the number requested."
                else:
                    if len(taxon_frequency) == 1:
                        error_message = f"{username} only has {len(taxon_frequency)} observation which is not sufficient for the number requested."
                    else:
                        error_message = f"{username} only has {len(taxon_frequency)} observations which is not sufficient for the number requested."
            return render_template('index.html', error=error_message)

        sorted_taxa = sorted(taxon_frequency.items(), key=lambda item: item[1]["count"])[:number_of_results]

        results = []
        failed_taxon_ids = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_taxon = {
                executor.submit(fetch_taxon_info, taxon_id): taxon_id
                for taxon_id, _ in sorted_taxa
            }
            for future in concurrent.futures.as_completed(future_to_taxon):
                taxon_id = future_to_taxon[future]
                try:
                    taxon_name, image_url = future.result()
                    if taxon_name is None:
                        logger.error(f"Failed to fetch taxon name for Taxon ID {taxon_id}")
                        failed_taxon_ids.append(taxon_id)
                        continue
                    observations_count = taxon_frequency[taxon_id]["count"]
                    taxon_type = taxon_frequency[taxon_id]["type"]
                    quality_grade = taxon_frequency[taxon_id]["quality_grade"]
                    observation_url = f"https://www.inaturalist.org/observations?user_id={username}&taxon_id={taxon_id}"
                    results.append((taxon_name, taxon_id, observations_count, taxon_type, observation_url, image_url, quality_grade))
                except Exception as exc:
                    logger.error(f"Error fetching taxon name for Taxon ID {taxon_id}: {exc}")
                    return render_template('index.html', error=f"Error fetching taxon name for Taxon ID {taxon_id}: {exc}")

        # Sequentially fetch taxon names for failed taxon IDs
        for taxon_id in failed_taxon_ids:
            try:
                taxon_name, image_url = fetch_taxon_info(taxon_id)
                if taxon_name is None:
                    logger.error(f"Failed to fetch taxon name for Taxon ID {taxon_id} after sequential retry")
                    taxon_name = f"Unknown (ID: {taxon_id})"
                observations_count = taxon_frequency[taxon_id]["count"]
                taxon_type = taxon_frequency[taxon_id]["type"]
                quality_grade = taxon_frequency[taxon_id]["quality_grade"]
                observation_url = f"https://www.inaturalist.org/observations?user_id={username}&taxon_id={taxon_id}"
                results.append((taxon_name, taxon_id, observations_count, taxon_type, observation_url, image_url, quality_grade))
            except Exception as exc:
                logger.error(f"Error fetching taxon name for Taxon ID {taxon_id} after sequential retry: {exc}")
                return render_template('index.html', error=f"Error fetching taxon name for Taxon ID {taxon_id} after sequential retry: {exc}")

        results.sort(key=lambda x: x[2])
        return render_template('index.html', results=results, number_of_results=number_of_results, species_type=species_type, username=username)

    return render_template('index.html')

# Custom filter to format numbers with commas
@bp.app_template_filter('format_number')
def format_number(value):
    return "{:,}".format(value)