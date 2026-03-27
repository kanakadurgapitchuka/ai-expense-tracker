def predict_category_wise(data):
    return "General"

def predict_category_wise(expenses):

    if len(expenses) < 3:
        return {}

    df = pd.DataFrame(expenses)

    if "date" not in df.columns or "amount" not in df.columns:
        return {}

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna()

    df["month"] = df["date"].dt.to_period("M")

    predictions = {}

    categories = df["category"].unique()

    for cat in categories:

        cat_df = df[df["category"] == cat]

        monthly = cat_df.groupby("month")["amount"].sum().reset_index()

        if len(monthly) < 2:
            continue

        monthly["month_index"] = range(len(monthly))

        X = monthly[["month_index"]]
        y = monthly["amount"]

        model = LinearRegression()
        model.fit(X, y)

        next_index = [[len(monthly)]]
        prediction = model.predict(next_index)[0]

        predictions[cat] = round(float(prediction), 2)

    return predictions
