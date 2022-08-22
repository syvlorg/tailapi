from itertools import chain, combinations
test = [ "-r", "-e", "-p", "\"tag:client\"", "\"tag:server\"", "\"tag:relay\"", "\"tag:bootstrap\"", "\"tag:abhijit\"", "\"tag:jayita\"" ]
def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s)+1))
testing = sorted(powerset(test), key = lambda k: k[0] if k else "")
for item in testing:
    print(item)
print(len(testing))
