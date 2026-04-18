# SFD Classic - parsed outputs

Unless noted, values come from `pandas.DataFrame` rows returned by `parse()`. List-typed cells hold Python lists aligned to species or product indices where the parser builds them that way.

## PRD (`.prd`)

`PRDParser.parse()` returns: `header`, `machine`, `objects`, `species_groups`, `products`, `statistics`.

| Name                           | Type      | Part           |
| ------------------------------ | --------- | -------------- |
| `creation_date`                | str       | header         |
| `modification_date`            | str       | header         |
| `application_version_created`  | str       | header         |
| `application_version_modified` | str       | header         |
| `machine_base_manufacturer`    | str       | machine        |
| `machine_base_model`           | str       | machine        |
| `contract_number`              | str       | objects        |
| `object_name`                  | str       | objects        |
| `species_group_key`            | str       | species_groups |
| `species_group_name`           | str       | species_groups |
| `product_key`                  | str       | products       |
| `product_name`                 | str       | products       |
| `total_stems`                  | int       | statistics     |
| `stems_per_species`            | list[int] | statistics     |
| `species_names`                | list[str] | statistics     |

## PRI (`.pri`)

`PRIParser.parse()` returns: `header`, `machine`, `objects`, `buyer_vendor`, `calibration`, `apt_history`, `species_groups`, `products`, `price_matrices`, `operators`, `production_statistics`, `log_codes`, `tree_codes`, `additional_info`, `logs`.

| Name                                | Type        | Part                  |
| ----------------------------------- | ----------- | --------------------- |
| `creation_date`                     | str         | header                |
| `modification_date`                 | str         | header                |
| `valid_from_date`                   | str         | header                |
| `start_date`                        | str         | header                |
| `application_version`               | str         | header                |
| `machine_id`                        | str         | machine               |
| `machine_base_manufacturer`         | str         | machine               |
| `machine_base_model`                | str         | machine               |
| `machine_serial`                    | str         | machine               |
| `head_model`                        | str         | machine               |
| `contract_number`                   | str         | objects               |
| `contract_number_swedish`           | str         | objects               |
| `operator_id`                       | str         | objects               |
| `object_name`                       | str         | objects               |
| `object_status`                     | str         | objects               |
| `buyer_text`                        | str         | buyer_vendor          |
| `buyer_matrix_text`                 | str         | buyer_vendor          |
| `vendor_code`                       | str         | buyer_vendor          |
| `vendor_name`                       | str         | buyer_vendor          |
| `vendor_address`                    | str         | buyer_vendor          |
| `vendor_email`                      | str         | buyer_vendor          |
| `vendor_phone`                      | str         | buyer_vendor          |
| `subcontractor_code`                | str         | buyer_vendor          |
| `subcontractor_name`                | str         | buyer_vendor          |
| `subcontractor_address`             | str         | buyer_vendor          |
| `subcontractor_email`               | str         | buyer_vendor          |
| `subcontractor_phone`               | str         | buyer_vendor          |
| `num_length_calibrations`           | int         | calibration           |
| `num_length_cal_per_species`        | list[int]   | calibration           |
| `num_length_positions`              | list[int]   | calibration           |
| `length_cal_dates`                  | list[str]   | calibration           |
| `length_cal_reasons`                | list[str]   | calibration           |
| `length_cal_reason_codes`           | list[int]   | calibration           |
| `length_positions_cm`               | list[int]   | calibration           |
| `length_corrections_mm`             | list[int]   | calibration           |
| `length_corrections_butt_mm`        | list[int]   | calibration           |
| `num_diameter_calibrations`         | int         | calibration           |
| `num_diameter_cal_per_species`      | list[int]   | calibration           |
| `num_diameter_positions`            | list[int]   | calibration           |
| `diameter_cal_dates`                | list[str]   | calibration           |
| `diameter_cal_reasons`              | list[str]   | calibration           |
| `diameter_cal_reason_codes`         | list[int]   | calibration           |
| `diameter_positions_mm`             | list[int]   | calibration           |
| `diameter_corrections_mm`           | list[int]   | calibration           |
| `diameter_correction_a`             | list[float] | calibration           |
| `diameter_correction_b`             | list[float] | calibration           |
| `num_changes`                       | int         | apt_history           |
| `change_dates`                      | list[str]   | apt_history           |
| `change_variables`                  | list[str]   | apt_history           |
| `change_machine_ids`                | list[str]   | apt_history           |
| `last_reset_date`                   | str         | apt_history           |
| `reset_signature`                   | str         | apt_history           |
| `species_group_key`                 | str         | species_groups        |
| `species_group_name`                | str         | species_groups        |
| `species_code`                      | int         | species_groups        |
| `num_bark_params`                   | int         | species_groups        |
| `num_diameter_breaks`               | int         | species_groups        |
| `bark_function_type`                | int         | species_groups        |
| `product_key`                       | str         | products              |
| `product_name`                      | str         | products              |
| `product_code`                      | str         | products              |
| `species_group_key`                 | str         | products              |
| `product_additional_id`             | str         | products              |
| `product_modification_date`         | str         | products              |
| `product_additional_info`           | str         | products              |
| `product_unique_id`                 | int         | products              |
| `num_diameter_classes`              | int         | products              |
| `num_length_classes`                | int         | products              |
| `product_group_number`              | int         | products              |
| `diameter_limits_mm`                | list[int]   | price_matrices        |
| `diameter_class_names`              | list[str]   | price_matrices        |
| `length_limits_cm`                  | list[int]   | price_matrices        |
| `grades`                            | list[int]   | price_matrices        |
| `num_grades_used`                   | int         | price_matrices        |
| `grade_descriptions`                | list[str]   | price_matrices        |
| `price_categories`                  | list[int]   | price_matrices        |
| `density_ub_kg_m3`                  | list[int]   | price_matrices        |
| `density_ob_kg_m3`                  | list[int]   | price_matrices        |
| `operator_key`                      | str         | operators             |
| `operator_name`                     | str         | operators             |
| `num_stems`                         | int         | production_statistics |
| `total_stems_site`                  | int         | production_statistics |
| `num_multi_tree_occasions`          | int         | production_statistics |
| `num_multi_tree_stems`              | int         | production_statistics |
| `num_multi_tree_occasions_measured` | int         | production_statistics |
| `num_stem_bunches`                  | int         | production_statistics |
| `total_merchantable_volume_m3_ub`   | list[int]   | production_statistics |
| `estimated_logs_bunched`            | int         | production_statistics |
| `total_log_bunches_site`            | int         | production_statistics |
| `num_log_bunches`                   | int         | production_statistics |
| `num_logs`                          | int         | production_statistics |
| `total_logs_site`                   | int         | production_statistics |
| `distance_covered_km`               | float       | production_statistics |
| `distance_per_operator_km`          | list[int]   | production_statistics |
| `num_log_codes`                     | int         | log_codes             |
| `num_downgrade_codes`               | int         | log_codes             |
| `num_multi_tree_codes`              | int         | log_codes             |
| `log_codes`                         | list[int]   | log_codes             |
| `downgrade_codes`                   | list[int]   | log_codes             |
| `multi_tree_codes`                  | list[int]   | log_codes             |
| `num_log_data_fields`               | int         | log_codes             |
| `num_multi_tree_log_data_fields`    | int         | log_codes             |
| `num_tree_codes`                    | int         | tree_codes            |
| `num_multi_tree_codes`              | int         | tree_codes            |
| `num_multi_felling_codes`           | int         | tree_codes            |
| `tree_codes`                        | list[int]   | tree_codes            |
| `multi_tree_codes`                  | list[int]   | tree_codes            |
| `multi_felling_codes`               | list[int]   | tree_codes            |
| `num_tree_data_fields`              | int         | tree_codes            |
| `num_multi_tree_data_fields`        | int         | tree_codes            |
| `num_multi_felling_data_fields`     | int         | tree_codes            |
| `optional_text_to_machine`          | str         | additional_info       |
| `optional_text_from_machine`        | str         | additional_info       |
| `dbh_height_cm`                     | list[int]   | additional_info       |
| `dbh_derivation_distance_cm`        | list[int]   | additional_info       |
| `coord_ref_position`                | str         | additional_info       |
| `coord_type`                        | str         | additional_info       |
| `coord_system`                      | str         | additional_info       |
| `coord_start_latitude`              | str         | additional_info       |
| `coord_start_lat_direction`         | str         | additional_info       |
| `coord_start_longitude`             | str         | additional_info       |
| `coord_start_lon_direction`         | str         | additional_info       |
| `coord_start_altitude_m`            | str         | additional_info       |
| `coord_start_datetime`              | str         | additional_info       |
| `butt_diam_method`                  | list[int]   | additional_info       |
| `apteri_text`                       | str         | additional_info       |
| `apteri_datetime`                   | str         | additional_info       |
| `stand_age_mean_years`              | str         | additional_info       |
| `stand_age_std_dev_years`           | str         | additional_info       |

### PRI - `logs` table

`logs` is one row per log. Columns are **dynamic**: only log codes present in the file _and_ listed in `PRI_LOG_CODES` become columns;

| Name                  | Type | Part |
| --------------------- | ---- | ---- |
| `assortment_index`    | int  | logs |
| `species_index`       | int  | logs |
| `price_matrix_key`    | int  | logs |
| `stem_number`         | int  | logs |
| `log_number`          | int  | logs |
| `diameter_top_ob`     | int  | logs |
| `diameter_top_ub`     | int  | logs |
| `diameter_mid_ob`     | int  | logs |
| `diameter_mid_ub`     | int  | logs |
| `diameter_root_ob`    | int  | logs |
| `diameter_root_ub`    | int  | logs |
| `forced_cross_cut`    | int  | logs |
| `length_actual_cm`    | int  | logs |
| `length_class_cm`     | int  | logs |
| `volume_m3_custom`    | int  | logs |
| `volume_m3_sob`       | int  | logs |
| `volume_m3_sub`       | int  | logs |
| `volume_m3_top_ob`    | int  | logs |
| `volume_m3_top_ub`    | int  | logs |
| `volume_dl_custom`    | int  | logs |
| `volume_dl_sob`       | int  | logs |
| `volume_dl_sub`       | int  | logs |
| `bunch_diameter_top`  | int  | logs |
| `bunch_length`        | int  | logs |
| `bunch_volume_m3_sob` | int  | logs |
| `bunch_sequence_id`   | int  | logs |
| `bunch_index`         | int  | logs |
| `diameter_unknown_1`  | int  | logs |
| `diameter_unknown_2`  | int  | logs |

## APT (`.apt`)

`APTParser.parse()` returns a dict with one key, `price_matrix`, whose value is a plain `dict` (not a DataFrame).

| Name                               | Type      | Part         |
| ---------------------------------- | --------- | ------------ |
| `total_tree_species_count`         | list[int] | price_matrix |
| `assortments_per_species`          | list[int] | price_matrix |
| `diameter_classes_per_matrix`      | list[int] | price_matrix |
| `length_classes_per_matrix`        | list[int] | price_matrix |
| `tree_species_names`               | list[str] | price_matrix |
| `assortment_names`                 | list[str] | price_matrix |
| `diameter_class_limits_mm`         | list[int] | price_matrix |
| `length_class_limits`              | list[int] | price_matrix |
| `permitted_quality_grade_bitmasks` | list[int] | price_matrix |
| `relative_price_value_matrix_flat` | list[int] | price_matrix |

`APTParser.parse_raw_blocks()` returns `dict[tuple[int, int], str]` mapping `(group_id, variable_id)` to raw block text; it is not included in `parse()`.
