import argparse
import os.path

from financial.gain_loss_tools import (get_financial_quarter_data_br, get_financial_gain_loss_table,
                                       save_financial_gl_plots)
from financial.asset_value_indicators import (get_assets_value_indicators_br,
                                              get_assets_value_indicators_table)

from utils.utils_data import process_financial_gain_loss_df

def main(company: str):
    comp = "asbisc"
    #TODO: get br specific names mapping

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

    if os.path.exists("asset_value_ind_data_br.pkl"):
        with open("asset_value_ind_data_br.pkl", "rb") as f:
            import pickle
            asset_value_ind_data = pickle.load(f)

    else:
        asset_value_ind_data = get_assets_value_indicators_br(comp)
        with open("asset_value_ind_data_br.pkl", "wb") as f:
            import pickle
            pickle.dump(financial_data, f)

    #TODO: prepare flow to generate asset value indicators df
    df_asset_val_ind = get_assets_value_indicators_table(asset_value_ind_data)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Analyze dividends of a company.")
    parser.add_argument("-c", "--company", type=str, required=True, help="Company name")

    args = parser.parse_args()

    main(**vars(args))