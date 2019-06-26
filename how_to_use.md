# ecsub 使用の手引き

## ecsub とは

Amazon Elastic Container Servise (Amazon ECS) を使用したバッチジョブ実行エンジンです。  
Amazon Elastic Compute Cloud (Amazon EC2) にインスタンスを作成して docker コンテナを構築しバッチジョブを実行します。  
入出力ソースとして Amazon Simple Storage Service (Amazon S3) を使用することができます。  

## とりあえず実行する

```
ecsub submit \
--script ~/gitlab/ecsub-testdata/examples-iret/run-wordcount.sh \
--tasks ~/gitlab/ecsub-testdata/examples-iret/tasks-wordcount-1.tsv \
--aws-s3-bucket  s3://aokad-ana-singapore/ecsub-test \
--image python:2.7.14 \
--aws-ec2-instance-type t2.micro \
--disk-size 1
```

## 実行中のログを確認する

ecsub はタスクのログを AWSCoudwatch に保存します。

```
2018-12-18 16:49:44.473816 [tasks-wordcount-1-qyD56:000] For detail, see log-file: https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logEventViewer:group=ecsub-tasks-wordcount-1-qyD56;stream=ecsub/tasks-wordcount-1-qyD56_task/330419b5-c48a-4483-bb1a-1c14d6625a04
```

## 途中で止めたい

ecsub 実行中のコンソールで Ctrl-C を入力してください。  
その後以下のような終了処理が走りますので、そのままお待ちください。

```
KeyboardInterrupt
2018-12-18 16:19:49.683496 [tasks-wordcount-1-nk2Vs] + aws ec2 terminate-instances --instance-ids i-067e2dfc2a7d3809b i-01bfa1f3a4d17ac63
2018-12-18 16:19:54.675539 [tasks-wordcount-1-nk2Vs] + aws ec2 wait instance-terminated --instance-ids i-067e2dfc2a7d3809b i-01bfa1f3a4d17ac63
2018-12-18 16:20:45.795659 [tasks-wordcount-1-nk2Vs] + aws ec2 cancel-spot-instance-requests --spot-instance-request-ids sir-e5piabrh sir-2mvrbq6j sir-bnggbv4h
2018-12-18 16:20:51.735453 [tasks-wordcount-1-nk2Vs] + aws ecs delete-cluster --cluster arn:aws:ecs:ap-northeast-1:047717877309:cluster/tasks-wordcount-1-nk2Vs
2018-12-18 16:20:57.028853 [tasks-wordcount-1-nk2Vs] + aws ecs deregister-task-definition --task-definition arn:aws:ecs:ap-northeast-1:047717877309:task-definition/tasks-wordcount-1-nk2Vs:1
2018-12-18 16:21:02.446327 [tasks-wordcount-1-nk2Vs] + aws ec2 delete-key-pair --key-name tasks-wordcount-1-nk2Vs
```


## スポットインスタンスを使用する

`--spot` オプションをつけて実行してください。  
`--aws-ec2-instance-type` オプションの代わりに `--aws-ec2-instance-type-list`  オプションを使用することをお勧めします。  

`--aws-ec2-instance-type-list` オプションは指定された順にインスタンスタイプを使用し、ジョブが成功するまでリトライします。  
インスタンスのリストをカンマ区切りで優先度の高い順に記述してください。  

```
ecsub submit \
(省略)
--aws-ec2-instance-type-list m5.2xlarge,t3.2xlarge,m4.2xlarge,t2.2xlarge \
--spot
```

## ジョブのコストを知りたい

タスクごとに以下ファイルに出力されています。

`/tmp/ecsub/{job}/log/summary.xxx.log`

## エラーかな？と思ったら

### remainingResources(MEMORY)

```
[ERROR] remainingResources(MEMORY): xxx
```

メモリが足りていない

```
ecsub submit \
(省略)
--memory 30
```

### There is no Spot capacity

```
[ERROR] Failure request-spot-instances. [Status] open [Code] capacity-not-available [Message] There is no Spot capacity available that matches your request.
```

スポットインスタンスを起動するための空きがAWSにありません。  
時間を空けて再度挑戦するか、別のインスタンスタイプを指定してください。

### instance-type xxx is not supported in ecsub

```
[ERROR] instance-type m5d.2xlarge is not supported in ecsub.
```

指定されたインスタンスタイプは現在、ecsubで対応していません。
別のインスタンスタイプをお試しください。

対応しているインスタンスタイプは "{ecsub}/scripts.ecsub/aws_config.py" の INSTANCE_TYPE で定義されています。

### ecsub タスクのログで `left device is no space` エラー

起動したインスタンスでディスクが不足しています。
ディスクを増やして再度実行してください。

ディスク用量は `ecsub submit` コマンドの `--disk` オプションで指定できます。単位は Gib です。
