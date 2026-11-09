from . import evaluator, planner

VERSION = "interview-50-50-v1"


def band(score):
    return ("Kém" if score<30 else "Yếu" if score<50 else "Trung bình" if score<70
            else "Tốt" if score<90 else "Rất tốt")


def summarize(answers,plan,role,previous,user_id):
    turns=[]
    for ident,answer in enumerate(answers,1):
        question=plan[answer.position]
        domains=question.get("domains",planner.default_domains(question["kind"]))
        turns.append({"turn_id":ident,"position":answer.position,"turn":answer.turn,"question":answer.question,
                      "transcript":answer.transcript,"skipped":answer.evaluation.get("skipped",False),"domains":domains,
                      "reference_topics":question.get("topic_criteria",[])})
    level=plan[0].get("level","intern")
    groups=list(evaluator.batches(turns))
    results, summary = {}, None
    if any(t["transcript"] and t["domains"] for t in turns):
        for group in groups:
            graded, summary=evaluator.evaluate(group,role,level,user_id,whole=len(groups)==1)
            results.update(graded)
    domains={}
    for domain,labels in evaluator.RUBRIC.items():
        by_question={}
        for turn in turns:
            if domain not in turn["domains"]:
                continue
            row=next((r for r in results.get(turn["turn_id"],[]) if r["domain"]==domain),None)
            previous_marks=by_question.get(turn["position"],[0]*4)
            by_question[turn["position"]]=[max(a,b) for a,b in zip(previous_marks,row["scores"] if row else [0]*4)]
        count=len(by_question)
        means=[sum(row[i] for row in by_question.values())/max(count,1) for i in range(4)]
        points=round(2.5*sum(means),1)
        domains[domain]={"score":points,"band":band(points),"question_count":count,
                         "criteria":[{"label":label,"score":round(mean*2.5,1)} for label,mean in zip(labels,means)]}
    score=round(sum(d["score"] for d in domains.values())/2,1)
    for turn in turns:
        turn["results"]=results.get(turn["turn_id"],[])
    if results and len(groups)>1:
        evidence=[{"turn_id":t["turn_id"],"question":t["question"],"results":t["results"]} for t in turns if t["results"]]
        summary=evaluator.synthesize(role,level,evidence,domains,user_id)
    positive={ident for ident,rows in results.items() if any(any(row["scores"]) for row in rows)}
    def remarks(items,valid):
        return [{"text":r.text,"turn_ids":list(dict.fromkeys(i for i in r.turn_ids if i in valid))}
                for r in items if valid.intersection(r.turn_ids)]
    return {"version":VERSION,"score":score,"band":band(score),"domains":domains,"answers":turns,
            "previous_score":previous,"delta":round(score-previous,1) if previous is not None else None,
            "strengths":remarks(summary.strengths,positive) if summary else [],
            "limitations":remarks(summary.limitations,set(results)) if summary else [],
            "practice":summary.practice if summary else ["Cần thêm câu trả lời có nội dung để đánh giá."],
            "group_count":len(groups)}
