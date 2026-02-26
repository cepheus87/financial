import argparse
import os.path

from financial.gain_loss_tools import (get_financial_quarter_data_br, get_financial_gain_loss_table,
                                       save_financial_gl_plots)
from financial.asset_value_indicators import (get_assets_value_indicators_br,
                                              get_assets_value_indicators_table,
                                              save_assets_value_indicators_plots)
from financial.profitability_indicators import (get_profitability_indicators_br, get_profitability_indicators_table,
                                                save_profitability_indicators_plots)

from utils.utils_data import (process_financial_gain_loss_df, process_profitability_indicators_df,
                              process_assets_value_indicators_df, DataCacher)

def main_test(company: str, download: bool):
    # comp = "asbisc"
    comp = company
    #TODO: start saving and loading data files after downloading, make functions for that

    if download:
        financial_data = get_financial_quarter_data_br(comp)
        with open("financial_data_br.pkl", "wb") as f:
            import pickle
            pickle.dump(financial_data, f)
    else:
        if os.path.exists("financial_data_br.pkl"):
            with open("financial_data_br.pkl", "rb") as f:
                import pickle
                financial_data = pickle.load(f)

        else:
            financial_data = get_financial_quarter_data_br(comp)
            with open("financial_data_br.pkl", "wb") as f:
                import pickle
                pickle.dump(financial_data, f)



    df_financial = get_financial_gain_loss_table(financial_data)
    df_financial = process_financial_gain_loss_df(df_financial)

    save_financial_gl_plots(company, df_financial)
    #TODO: data analysis and drawing

    if download:
        asset_value_ind_data = get_assets_value_indicators_br(comp)
        with open("asset_value_ind_data_br.pkl", "wb") as f:
            import pickle
            pickle.dump(asset_value_ind_data, f)
    else:
        if os.path.exists("asset_value_ind_data_br.pkl"):
            with open("asset_value_ind_data_br.pkl", "rb") as f:
                import pickle
                asset_value_ind_data = pickle.load(f)

        else:
            asset_value_ind_data = get_assets_value_indicators_br(comp)
            with open("asset_value_ind_data_br.pkl", "wb") as f:
                import pickle
                pickle.dump(asset_value_ind_data, f)

    df_asset_val_ind = get_assets_value_indicators_table(asset_value_ind_data)
    df_asset_val_ind = process_assets_value_indicators_df(df_asset_val_ind)

    #TODO: use shares_price_num in dividend analysis
    df_shares_price_num = df_asset_val_ind[df_asset_val_ind.columns[:5]]

    save_assets_value_indicators_plots(company, df_asset_val_ind)

    if download:
        profitability_ind_data = get_profitability_indicators_br(comp)
        with open("profitability_ind_data_br.pkl", "wb") as f:
            import pickle
            pickle.dump(profitability_ind_data, f)
    else:
        if os.path.exists("profitability_ind_data_br.pkl"):
            with open("profitability_ind_data_br.pkl", "rb") as f:
                import pickle
                profitability_ind_data = pickle.load(f)

        else:
            profitability_ind_data = get_profitability_indicators_br(comp)
            with open("profitability_ind_data_br.pkl", "wb") as f:
                import pickle
                pickle.dump(profitability_ind_data, f)

    df_profitability = get_profitability_indicators_table(profitability_ind_data)
    df_profitability = process_profitability_indicators_df(df_profitability)

    save_profitability_indicators_plots(company, df_profitability)

def main(company: str, download: bool):
    comp = "asbis"
    #TODO: start saving and loading data files after downloading, make functions for that

    data_cacher = DataCacher(company, "df_financial", "financial", download,
                             getter=get_financial_quarter_data_br, processor=get_financial_gain_loss_table)
    df_financial = data_cacher.load_df_data()

    # financial_data = get_financial_quarter_data_br(company)
    # df_financial = get_financial_gain_loss_table(financial_data)
    df_financial = process_financial_gain_loss_df(df_financial)

    save_financial_gl_plots(company, df_financial)

    # TODO: check if all drawing are done in save_financial_gl_plots
    data_cacher = DataCacher(company, "df_asset_val_ind", "financial", download,
                             getter=get_assets_value_indicators_br, processor=get_assets_value_indicators_table)
    df_asset_val_ind = data_cacher.load_df_data()

    # asset_value_ind_data = get_assets_value_indicators_br(company)
    # df_asset_val_ind = get_assets_value_indicators_table(asset_value_ind_data)
    df_asset_val_ind = process_assets_value_indicators_df(df_asset_val_ind)

    #TODO: use shares_price_num in dividend analysis
    df_shares_price_num = df_asset_val_ind[df_asset_val_ind.columns[:5]]

    save_assets_value_indicators_plots(company, df_asset_val_ind)

    data_cacher = DataCacher(company, "df_profitability", "financial", download,
                             getter=get_profitability_indicators_br, processor=get_profitability_indicators_table)
    df_profitability = data_cacher.load_df_data()

    # profitability_ind_data = get_profitability_indicators_br(company)
    # df_profitability = get_profitability_indicators_table(profitability_ind_data)
    df_profitability = process_profitability_indicators_df(df_profitability)

    save_profitability_indicators_plots(company, df_profitability)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analyze dividends of a company.")
    parser.add_argument("-c", "--company", type=str, required=True, help="Company name")
    parser.add_argument("-t", "--test", action="store_true", help="Run in test mode with sample data")
    parser.add_argument("-d", "--download", action="store_true", help="Download data from the web (default: False, use cached data if available)")

    args = parser.parse_args()

    if args.test:
        print("Running in test mode with sample data...")
        main_test(args.company, args.download)
    else:
        main(args.company, args.download)

