import pandas as pd

# Load data
df = pd.read_csv("test.csv")  # replace with your actual filename

# Get timestamp column
time = df['timestamp']

# Compute time differences
dt = time.diff()

# Loop over each column except timestamp
for col in df.columns:
    if col == 'timestamp':
        continue
    if col.endswith("_hat"):
        continue
    # Compute rate of change
    df[f'd_{col}__dt'] = df[col].diff() / dt

# Optionally: drop the first row which contains NaNs due to diff()
df = df.dropna().reset_index(drop=True)

# Save or inspect
# print(df)
df.to_csv("output_with_derivatives.csv", index=False)

