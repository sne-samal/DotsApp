def encode_coefficients(coefficients):
    encoded_coefficients = []
    for coefficient in coefficients:
        encoded_coefficient = ''.join(chr(ord('A') + int(digit)) for digit in str(coefficient) if digit.isdigit())
        encoded_coefficients.append(encoded_coefficient)
    return '_'.join(encoded_coefficients)

def main():
    coefficients = []
    for i in range(5):
        while True:
            try:
                coefficient = round(float(input(f"Enter coefficient {i+1}: ")) * 10000, 3)
                if coefficient >= 0:
                    coefficients.append(coefficient)
                    break
                else:
                    print("Please enter a non-negative number.")
            except ValueError:
                print("Invalid input. Please enter a number.")
    encoded_string = encode_coefficients(coefficients)
    print("Encoded coefficients:", encoded_string)

if __name__ == "__main__":
    main()
