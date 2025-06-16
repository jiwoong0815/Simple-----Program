import json
import uuid
import os

def transform_data():
    current_script_directory = os.path.dirname(os.path.abspath(__file__))
    source_file_path = os.path.join(current_script_directory, '..', '..', '..', 'Downloads', '업체별_금액.json')
    output_file_path = os.path.join(current_script_directory, 'price_profiles.json')

    try:
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Source file not found at {source_file_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {source_file_path}. Details: {e}")
        return
    except Exception as e:
        print(f"An unexpected error occurred while reading the source file: {e}")
        return

    all_unique_products = set() # Stores tuples of (model, product, spec)

    # Step 1: Collect all unique product definitions
    for _, items_list in source_data.items():
        if items_list is None:
            continue
        for item in items_list:
            if not isinstance(item, dict):
                continue
            
            model_name = item.get("모델명")
            product_name = item.get("제품명")
            spec = item.get("규격")

            if model_name is not None and product_name is not None and spec is not None:
                model_name_stripped = str(model_name).strip()
                product_name_stripped = str(product_name).strip()
                spec_stripped = str(spec).strip()
                
                if model_name_stripped and product_name_stripped and spec_stripped:
                    all_unique_products.add((model_name_stripped, product_name_stripped, spec_stripped))

    new_profiles = []

    # Step 2: Process each company
    for company_group_key, items_list_for_group in source_data.items():
        company_names_in_group = company_group_key.split('/')
        
        for company_name_raw in company_names_in_group:
            company_name = company_name_raw.strip()
            if not company_name:
                continue

            profile = {
                "id": str(uuid.uuid4()),
                "name": company_name,
                "item_prices": {}
            }

            # Store this company's specific prices from the source
            company_specific_prices = {}
            if items_list_for_group is not None:
                for item in items_list_for_group:
                    if not isinstance(item, dict):
                        continue

                    model_name = item.get("모델명")
                    product_name = item.get("제품명")
                    spec = item.get("규격")
                    price_val = item.get("price")

                    if model_name is not None and product_name is not None and spec is not None and price_val is not None:
                        model_name_stripped = str(model_name).strip()
                        product_name_stripped = str(product_name).strip()
                        spec_stripped = str(spec).strip()

                        if model_name_stripped and product_name_stripped and spec_stripped:
                            try:
                                price_float = float(price_val)
                                if price_float > 0.0: # Only store valid, non-zero prices
                                    composite_key = f"{model_name_stripped}|{product_name_stripped}|{spec_stripped}"
                                    company_specific_prices[composite_key] = f"{price_float:.1f}"
                            except (ValueError, TypeError):
                                continue
            
            # Populate item_prices for the profile using all_unique_products
            for prod_model, prod_name, prod_spec in all_unique_products:
                composite_key = f"{prod_model}|{prod_name}|{prod_spec}"
                # Use specific price if available, otherwise default to "0.0"
                price_to_set = company_specific_prices.get(composite_key, "0.0")
                profile["item_prices"][composite_key] = price_to_set
            
            if profile["item_prices"]: # Should always be true now if all_unique_products is not empty
                new_profiles.append(profile)
            elif not all_unique_products and not profile["item_prices"]: # Handle case of no products at all
                 new_profiles.append(profile)


    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(new_profiles, f, indent=4, ensure_ascii=False)
        print(f"Successfully transformed data and saved to {output_file_path} (with 0.0 for unknown prices).")
    except IOError:
        print(f"Error: Could not write to output file {output_file_path}")
    except Exception as e:
        print(f"An unexpected error occurred while writing the output file: {e}")

if __name__ == "__main__":
    transform_data()
