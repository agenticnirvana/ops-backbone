package agentops

import future.keywords.in

default allow = false

destructive_keywords := {"restart", "rollback", "kill", "delete", "scale-down"}

contains_destructive(text) {
  some keyword in destructive_keywords
  contains(lower(text), keyword)
}

allow {
  not contains_destructive(input.recommendation)
}

allow {
  input.severity == "P3"
  not contains_destructive(input.recommendation)
}

allow {
  contains_destructive(input.recommendation)
  input.severity == "P1"
}
