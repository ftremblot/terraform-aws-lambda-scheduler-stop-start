"""Tests for the instance scheduler class."""

import boto3

from moto import mock_autoscaling, mock_cloudwatch, mock_ec2

from package.scheduler.cloudwatch_handler import CloudWatchAlarmScheduler
from package.scheduler.instance_handler import InstanceScheduler

from .utils import launch_asg, launch_ec2_instances

import pytest


@pytest.mark.parametrize(
    "aws_region, tag_key, tag_value, result_count", [
        ("eu-west-1", "tostop", "true", 3),
        ("eu-west-2", "tostop", "true", 3),
        ("eu-west-2", "badtagkey", "badtagvalue", 0),
    ]
)
@mock_ec2
@mock_autoscaling
def test_list_ec2_instance(aws_region, tag_key, tag_value, result_count):
    """Verify list ec2 instances function."""
    client = boto3.client("ec2", region_name=aws_region)
    launch_ec2_instances(3, aws_region, "tostop", "true")
    ec2_scheduler = InstanceScheduler(aws_region)
    taglist = ec2_scheduler.list_instances(tag_key, tag_value)
    assert len(list(taglist)) == result_count


@pytest.mark.parametrize(
    "aws_region, tag_key, tag_value, result_count", [
        ("eu-west-1", "tostop", "true", {"Code": 16, "Name": "running"}),
        ("eu-west-2", "tostop", "true", {"Code": 16, "Name": "running"}),
        ("eu-west-2", "badtagkey", "badtagvalue", {"Code": 80, "Name": "stopped"}),
    ]
)
@mock_ec2
@mock_cloudwatch
@mock_autoscaling
def test_start_ec2_instance(aws_region, tag_key, tag_value, result_count):
    """Verify start ec2 instance function."""
    client = boto3.client("ec2", region_name=aws_region)
    launch_ec2_instances(3, aws_region, "tostop", "true")
    for ec2 in client.describe_instances()["Reservations"][0]["Instances"]:
        client.stop_instances(InstanceIds=[ec2["InstanceId"]])

    ec2_scheduler = InstanceScheduler(aws_region)
    ec2_scheduler.cloudwatch_alarm = CloudWatchAlarmScheduler(aws_region)
    ec2_scheduler.start(tag_key, tag_value)
    for ec2 in client.describe_instances()["Reservations"][0]["Instances"]:
        assert ec2["State"] == result_count


@pytest.mark.parametrize(
    "aws_region, tag_key, tag_value, result_count", [
        ("eu-west-1", "tostop", "true", {"Code": 80, "Name": "stopped"}),
        ("eu-west-2", "tostop", "true", {"Code": 80, "Name": "stopped"}),
        ("eu-west-2", "badtagkey", "badtagvalue", {"Code": 16, "Name": "running"}),
    ]
)
@mock_ec2
@mock_cloudwatch
@mock_autoscaling
def test_stop_ec2_instance(aws_region, tag_key, tag_value, result_count):
    """Verify stop ec2 instance function."""
    client = boto3.client("ec2", region_name=aws_region)
    launch_ec2_instances(3, aws_region, tag_key, tag_value)

    ec2_scheduler = InstanceScheduler(aws_region)
    ec2_scheduler.cloudwatch_alarm = CloudWatchAlarmScheduler(aws_region)
    ec2_scheduler.stop("tostop", "true")
    instances = client.describe_instances()["Reservations"][0]["Instances"]
    assert len(instances) == 3
    for instance in instances:
        assert instance["State"] == result_count


@pytest.mark.parametrize(
    "aws_region, tag_key, tag_value, result_count", [
        ("eu-west-1", "tostop", "true", {"Code": 16, "Name": "running"}),
        ("eu-west-2", "tostop", "true", {"Code": 16, "Name": "running"}),
    ]
)
@mock_ec2
@mock_cloudwatch
@mock_autoscaling
def test_do_not_stop_asg_instance(aws_region, tag_key, tag_value, result_count):
    client = boto3.client("ec2", region_name=aws_region)
    launch_asg(aws_region, tag_key, tag_value)

    ec2_scheduler = InstanceScheduler(aws_region)
    ec2_scheduler.cloudwatch_alarm = CloudWatchAlarmScheduler(aws_region)
    ec2_scheduler.stop("tostop", "true")
    instances = client.describe_instances()["Reservations"][0]["Instances"]
    assert len(instances) == 3
    for instance in instances:
        assert instance["State"] == result_count


@pytest.mark.parametrize(
    "aws_region, tag_key, tag_value, result_count", [
        ("eu-west-1", "tostop", "true", {"Code": 80, "Name": "stopped"}),
        ("eu-west-2", "tostop", "true", {"Code": 80, "Name": "stopped"}),
    ]
)
@mock_ec2
@mock_cloudwatch
@mock_autoscaling
def test_do_not_start_asg_instance(aws_region, tag_key, tag_value, result_count):
    client = boto3.client("ec2", region_name=aws_region)
    launch_asg(aws_region, tag_key, tag_value)
    instances = client.describe_instances()["Reservations"][0]["Instances"]
    for instance in instances:
        client.stop_instances(InstanceIds=[instance["InstanceId"]])

    ec2_scheduler = InstanceScheduler(aws_region)
    ec2_scheduler.cloudwatch_alarm = CloudWatchAlarmScheduler(aws_region)
    ec2_scheduler.start("tostop", "true")
    instances = client.describe_instances()["Reservations"][0]["Instances"]
    assert len(instances) == 3
    for instance in instances:
        assert instance["State"] == result_count
