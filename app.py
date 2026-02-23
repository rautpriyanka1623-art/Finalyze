from flask import Flask, render_template, request

app = Flask(__name__)

expenses = [] # this will store all expenses

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']

        expense = {
            'amount': amount,
            'category': category,
            'description': description
        }

        expenses.append(expense)

    return render_template('index.html', expenses=expenses)

if __name__ == '__main__':
    app.run(debug=True)