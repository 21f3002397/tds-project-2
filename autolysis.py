# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "numpy",
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "requests",
#   "scikit-learn",
#   "tenacity",
#   "chardet"
# ]
# ///
import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
from tenacity import retry, wait_fixed
import chardet

AIPROXY_TOKEN = os.environ["AIPROXY_TOKEN"]
file_name=os.path.splitext(os.path.basename(sys.argv[1]))[0]
extension=os.path.splitext(os.path.basename(sys.argv[1]))[1]
cwd=os.getcwd()
save_path=os.path.join(cwd,file_name)
fallback_save_path=os.path.join(cwd,file_name+extension)
print(save_path)
if not os.path.exists(save_path):
    os.makedirs(save_path)
if not os.path.exists(fallback_save_path):
    os.makedirs(fallback_save_path)



# Function to read the dataset
def load_dataset(file_path):
    try:
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        encoding = result['encoding']
        
        data = pd.read_csv(file_path, encoding=encoding)
        return data
    except Exception as e:
        print(f"Error loading file: {e}")
        return None
    
# Function to summarize the dataset
def summarize_dataset(data):
    try:
        summary = {
            "shape": data.shape,
            "columns": list(data.columns),
            "dtypes": data.dtypes.to_dict(),
            "missing_values": data.isnull().sum().to_dict(),
            "sample_data": data.head(5).to_dict(),
        }
        return summary
    except Exception as e:
        print(f"Error summarizing dataset: {e}")
        return None

# Function to analyze numeric data
def analyze_numeric(data):
    try:
        numeric_data = data.select_dtypes(include=[np.number])
        stats = numeric_data.describe().T
        correlation = numeric_data.corr()
        return stats, correlation
    except Exception as e:
        print(f"Error analyzing numeric data: {e}")
        return None, None

# Function to visualize correlations
def plot_correlation(correlation):
    try:
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation, annot=True, cmap="coolwarm")
        plt.title("Correlation Matrix")
        plt.savefig(os.path.join(save_path,"fig_1.png"))
        plt.savefig(os.path.join(fallback_save_path,"fig_1.png"))
    
    except Exception as e:
        print(f"Error plotting correlation matrix: {e}")

# Function to interact with LLM
@retry(wait=wait_fixed(0.3))
def ask_llm(prompt):
    try:
        url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions" 
        headers = {"Authorization": f"Bearer {AIPROXY_TOKEN}",
                   "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages":[
                {"role": "system", "content": "You are a statistical summariser. Given the data you have to summarise it in a web article format, highlighting the important features of the data. Don't use bland info like 'this is an outlier, that is not, this is the mean, that is the median, etc.' Give useful metrics that says a story about the data. Use proper markdown for headings and such, and you are encouraged to use tables in markdown as well. Limit your explanation to max 2000 words(excluding tables)"},
                {"role": "user", "content": prompt}
            ]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    finally:
        print("error occured")

# Main function to run analysis
def Analyse(file_path):
    data = load_dataset(file_path)
    if data is None:
        return

    # Summarize dataset
    summary = summarize_dataset(data)
    stats, correlation = analyze_numeric(data)

    if summary:
        if stats is not None:
            summary["numeric_stats"] = stats.to_dict()
        if correlation is not None:
            summary["correlation_matrix"] = correlation.to_dict()

        #print("Dataset Summary:", summary)
        
        # Send summary to LLM
        llm_response = ask_llm(f"Given the following dataset summary: {summary}, what analysis would you recommend?")
        try:
            print(llm_response.json())
        except:
            print(llm_response)
        with open(os.path.join(save_path,"README.md"),"w") as f:
            f.write(llm_response)
        with open(fallback_save_path,"w") as f:
            f.write(llm_response)



    if stats is not None:
        print("Numeric Data Stats:")
        print(stats)
        if correlation is not None:
            print("Correlation Matrix:")
            print(correlation)
            plot_correlation(correlation)

if __name__ == "__main__":
    # Replace 'your_file.csv' with your actual file path
    Analyse(os.path.basename(sys.argv[1]))
