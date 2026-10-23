"""Reviewed task specifications, behavioral cases and task-specific hints.

Difficulty labels describe increasing task demands, not calibrated learner ability.
Tests cover selected normal and boundary inputs, not exhaustive correctness or complexity.
Reference solutions belong only in the offline tests, never in student starter code.
"""


def entry(title, function, parameters, description, example, tests, hints):
    return dict(title=title, function=function, description=description, example=example,
                starter=f"def {function}({parameters}):\n    # Write your solution here\n    pass\n",
                tests=tests, hints=hints)


EXERCISES = {
    ("Recursion", "medium"): entry(
        "Sum a Nested List Recursively", "sum_nested", "values",
        "Write sum_nested(values) using recursion. The input is a finite list containing integers "
        "or nested lists of the same kind. Return the sum of all integers. An empty list sums to zero.",
        "sum_nested([1, [2, [-3]], 4]) = 4",
        [("Empty list", [[]], 0), ("Flat values", [[1, 2, 3]], 6),
         ("Nested and negative", [[1, [2, [-3]], 4]], 4),
         ("Empty sublists", [[[], [[], 5]]], 5), ("Only negatives", [[[-2], -5]], -7)],
        ["Separate the integer case from the nested-list case.",
         "An empty list contributes zero; use a recursive call for each sublist.",
         "Accumulate integers directly and add each recursive sublist sum to the same total."]),
    ("Recursion", "hard"): entry(
        "Recursive Binary Search", "recursive_search", "nums, target",
        "Write recursive_search(nums, target) using recursion to halve the search interval. "
        "nums is an ascending list of distinct integers. Return the target's original index or -1 if absent. "
        "Handle an empty list. Aim for logarithmic comparisons.",
        "recursive_search([2, 5, 9, 12], 9) = 2",
        [("Empty", [[], 3], -1), ("Middle", [[2, 5, 9, 12], 9], 2),
         ("Left boundary", [[-5, 0, 7], -5], 0), ("Right boundary", [[-5, 0, 7], 7], 2),
         ("Absent", [[1, 3, 5, 7], 4], -1), ("Single value", [[8], 8], 0)],
        ["Use a helper with left and right indices into the original list.",
         "Stop when left exceeds right. Compare the midpoint and recurse into only one half.",
         "Return the midpoint on equality; otherwise exclude it from the next interval and return the recursive result."]),
    ("Prime Numbers", "medium"): entry(
        "Prime Factorization", "prime_factors", "n",
        "Write prime_factors(n) for integers n >= 2. Return all prime factors in ascending order, "
        "including repetitions. Factor 12 as [2, 2, 3], not [2, 3].",
        "prime_factors(18) = [2, 3, 3]",
        [("Smallest input", [2], [2]), ("Repeated factors", [12], [2, 2, 3]),
         ("Prime", [29], [29]), ("Perfect square", [49], [7, 7]),
         ("Mixed factors", [90], [2, 3, 3, 5])],
        ["Repeatedly divide by the smallest divisor still present.",
         "Keep testing the same divisor after a successful division so repeated factors are retained.",
         "Increase the divisor only when it no longer divides the remaining number; append a remaining prime greater than one."]),
    ("Prime Numbers", "hard"): entry(
        "Primes in an Inclusive Range", "primes_in_range", "start, end",
        "Write primes_in_range(start, end) returning every prime in the inclusive integer range in ascending order. "
        "Values below 2 are never prime; return [] for a reversed range. Design for ranges ending up to 100000, "
        "using a sieve or another efficient method.",
        "primes_in_range(-2, 7) = [2, 3, 5, 7]",
        [("Negative lower bound", [-2, 7], [2, 3, 5, 7]), ("Inclusive prime", [13, 13], [13]),
         ("No primes", [14, 16], []), ("Reversed", [8, 2], []),
         ("Below two", [-10, 1], []), ("Upper range", [99980, 100000], [99989, 99991])],
        ["Generate prime information up to the upper bound, then select the requested interval.",
         "In a sieve, mark zero and one non-prime and cross out multiples of each surviving prime.",
         "Begin crossing out at p squared; collect unmarked integers between max(2, start) and end inclusively."]),
    ("Arrays", "medium"): entry(
        "Rotate a List to the Right", "rotate_right", "nums, k",
        "Write rotate_right(nums, k) returning a list rotated right by a non-negative integer k. "
        "The input may be empty, contain duplicates, and k may exceed the list length. Do not modify nums.",
        "rotate_right([1, 2, 3, 4], 1) = [4, 1, 2, 3]",
        [("Empty", [[], 5], []), ("One step", [[1, 2, 3, 4], 1], [4, 1, 2, 3]),
         ("Large rotation", [[1, 2, 3], 5], [2, 3, 1]), ("Zero rotation", [[2, 2, 3], 0], [2, 2, 3]),
         ("Single value", [[7], 100], [7])],
        ["A full rotation by the list length changes nothing.",
         "Handle the empty list before using k modulo its length.",
         "Split at length minus the normalized rotation and combine the tail with the head into a new list."]),
    ("Arrays", "hard"): entry(
        "Maximum Contiguous Subarray Sum", "max_subarray_sum", "nums",
        "Write max_subarray_sum(nums) for a non-empty list of integers. Return the largest sum of a "
        "non-empty contiguous subarray. All-negative input must return its largest element. Aim for O(n) time.",
        "max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) = 6",
        [("Mixed", [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], 6), ("All negative", [[-8, -2, -5]], -2),
         ("Single negative", [[-7]], -7), ("All positive", [[1, 2, 3]], 6),
         ("Restart interval", [[5, -10, 6]], 6), ("Zeros", [[0, 0]], 0)],
        ["Track the best sum ending at the current position as well as the best overall sum.",
         "Initialize from the first value, since the chosen subarray must be non-empty.",
         "At each value choose between starting again there and extending the previous sum, then update the overall best."]),
    ("Strings", "easy"): entry(
        "Count Vowels", "count_vowels", "text",
        "Write count_vowels(text) returning the count of ASCII vowels a, e, i, o, u in a string. "
        "Ignore letter case. Count repeated vowels separately; other characters do not count.",
        "count_vowels('Hello!') = 2",
        [("Empty", [""], 0), ("Mixed case", ["AEiou"], 5), ("Sentence", ["Hello!"], 2),
         ("No vowels", ["rhythm 123"], 0), ("Repeats", ["Bookkeeper"], 5)],
        ["Check each character against a small collection of vowels.",
         "Normalize the character's case before testing membership.",
         "Start a counter at zero, increment for every vowel and return the final count."]),
    ("Strings", "medium"): entry(
        "Compare Anagrams", "are_anagrams", "left, right",
        "Write are_anagrams(left, right) returning True if two ASCII strings have the same character "
        "counts after ignoring case and all whitespace. Punctuation remains significant; repeated letters matter.",
        "are_anagrams('Dormitory', 'Dirty room') = True",
        [("Case and spaces", ["Dormitory", "Dirty room"], True), ("Repeated counts", ["aab", "abb"], False),
         ("Empty", ["", " \t"], True), ("Punctuation significant", ["ab!", "ab"], False),
         ("Same punctuation", ["a! B", "b!a"], True)],
        ["Remove only whitespace and normalize case in both strings.",
         "Presence alone is insufficient; repeated characters must have equal counts.",
         "Compare sorted normalized characters or their frequency dictionaries, including punctuation."]),
    ("Strings", "hard"): entry(
        "Longest Substring Without Repeats", "longest_unique_length", "text",
        "Write longest_unique_length(text) returning the length of the longest contiguous substring "
        "with no repeated characters. Compare characters case-sensitively; spaces are characters. Aim for O(n) time.",
        "longest_unique_length('abba') = 2",
        [("Empty", [""], 0), ("Repeated", ["aaaa"], 1), ("Do not move backwards", ["abba"], 2),
         ("Sliding window", ["pwwkew"], 3), ("Case sensitive", ["aAb"], 3),
         ("Space counts", ["a b a"], 3)],
        ["Maintain a window that contains only distinct characters.",
         "Store each character's most recent position and move the left edge past a duplicate inside the window.",
         "Never move the left edge backwards; update the best length after processing each character."]),
    ("Python Functions", "easy"): entry(
        "Clamp a Value", "clamp", "value, lower, upper",
        "Write clamp(value, lower, upper). Return lower if value is below lower, upper if above upper, "
        "otherwise value. Inputs are numbers with lower <= upper. Return the result rather than printing it.",
        "clamp(12, 0, 10) = 10",
        [("Below", [-4, 0, 10], 0), ("Above", [12, 0, 10], 10), ("Inside", [4, 0, 10], 4),
         ("Equal bounds", [9, 3, 3], 3), ("Negative bounds", [-5, -8, -2], -5)],
        ["Think about three possible regions for the input value.",
         "Check the lower and upper bounds and return immediately when a value lies outside them.",
         "If neither boundary condition applies, return value itself. Equality is already within range."]),
    ("Python Functions", "medium"): entry(
        "Operation Dispatcher", "calculate", "operation, a, b",
        "Write calculate(operation, a, b). operation is one of 'add', 'subtract', 'multiply', 'divide'. "
        "Return the corresponding numeric result, preserving operand order. Division uses / and b is non-zero for divide.",
        "calculate('subtract', 8, 3) = 5",
        [("Add", ["add", 2, 3], 5), ("Operand order", ["subtract", 3, 8], -5),
         ("Multiply", ["multiply", -2, 4], -8), ("Division", ["divide", 3, 2], 1.5),
         ("Zero result", ["multiply", 0, 5], 0)],
        ["Separate selecting an operation from calculating its result.",
         "Use branches or a dictionary of small helper functions; preserve a then b for subtraction and division.",
         "Return from every supported operation, and use ordinary division rather than floor division."]),
    ("Python Functions", "hard"): entry(
        "Composable Numeric Pipeline", "run_pipeline", "value, operations",
        "Write run_pipeline(value, operations) applying operations in order and returning the final number. "
        "Each operation is a pair [name, operand], where name is 'add', 'multiply' or 'subtract'. "
        "Use reusable functions to implement the operations. An empty pipeline returns the initial value.",
        "run_pipeline(3, [['add', 2], ['multiply', 4]]) = 20",
        [("Empty", [3, []], 3), ("Composition", [3, [["add", 2], ["multiply", 4]]], 20),
         ("Order matters", [3, [["multiply", 4], ["add", 2]]], 14),
         ("Subtraction", [10, [["subtract", 3], ["subtract", 2]]], 5),
         ("Negative and zero", [-2, [["multiply", 0], ["add", -3]]], -3)],
        ["Represent each operation by a reusable function and keep one current value.",
         "Look up the function for each operation name, then apply it to the current value and operand.",
         "Walk through operations in their original order, replacing the current value each time; return it after the loop."]),
    ("Searching Algorithms", "easy"): entry(
        "Find the First Matching Index", "linear_search", "nums, target",
        "Write linear_search(nums, target) returning the first index equal to target in an unsorted list "
        "of integers, or -1 if no match exists. The list can be empty or contain duplicates.",
        "linear_search([4, 2, 4], 4) = 0",
        [("Empty", [[], 1], -1), ("First duplicate", [[4, 2, 4], 4], 0),
         ("Last", [[3, 1, 9], 9], 2), ("Absent", [[1, 2], 3], -1), ("Negative", [[0, -1], -1], 1)],
        ["Inspect elements in order, keeping track of their indices.",
         "Return as soon as you find a match to preserve the first matching index.",
         "Only return -1 after the entire list has been examined without a match."]),
    ("Searching Algorithms", "medium"): entry(
        "Iterative Binary Search", "binary_search", "nums, target",
        "Write binary_search(nums, target) for an ascending list of distinct integers. Return the target's "
        "index, or -1 if absent. Handle empty input and use an iterative interval-halving algorithm.",
        "binary_search([2, 5, 9, 12], 5) = 1",
        [("Empty", [[], 3], -1), ("Middle", [[2, 5, 9, 12], 5], 1),
         ("Left", [[-5, 0, 8], -5], 0), ("Right", [[-5, 0, 8], 8], 2),
         ("Absent", [[1, 3, 5], 4], -1), ("Single", [[7], 7], 0)],
        ["Maintain left and right bounds and examine their midpoint.",
         "Discard the half that cannot contain the target, excluding the midpoint after a mismatch.",
         "Loop while left <= right. Return the midpoint on equality, or -1 when the interval becomes empty."]),
    ("Searching Algorithms", "hard"): entry(
        "Lower Bound with Duplicate Values", "lower_bound", "nums, target",
        "Write lower_bound(nums, target) returning the first index whose value is >= target in an "
        "ascending list of integers with possible duplicates. Return len(nums) if no such value exists. "
        "Use binary search with O(log n) comparisons; an empty input returns 0.",
        "lower_bound([1, 2, 2, 4], 2) = 1",
        [("Empty", [[], 2], 0), ("First duplicate", [[1, 2, 2, 4], 2], 1),
         ("Insertion gap", [[1, 3, 5], 4], 2), ("After last", [[1, 3], 9], 2),
         ("Before first", [[2, 4], 1], 0), ("All equal", [[3, 3, 3], 3], 0)],
        ["Search for an insertion position, including the position after the last element.",
         "When the midpoint is >= target, it may be the answer but an earlier qualifying position may exist.",
         "Use a half-open [left, right) interval. Move right to mid for qualifying values, otherwise move left to mid + 1."]),
}


def hints_for(task):
    item = EXERCISES.get((task.concept_name, task.difficulty))
    return item["hints"] if item and item["title"] == task.title else None
