# Copyright 2020 kubeflow.org
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kfp import dsl
from kfp_tekton.tekton import CEL_ConditionOp


def random_num_op(low, high):
    """Generate a random number between low and high."""
    return dsl.ContainerOp(
        name='Generate random number',
        image='python:alpine3.6',
        command=['sh', '-c'],
        arguments=['python -c "import random; print(random.randint($0, $1))" | tee $2', str(low), str(high), '/tmp/output'],
        file_outputs={'output': '/tmp/output'}
    )


def flip_coin_op():
    """Flip a coin and output heads or tails randomly."""
    return dsl.ContainerOp(
        name='Flip coin',
        image='python:alpine3.6',
        command=['sh', '-c'],
        arguments=['python -c "import random; result = \'heads\' if random.randint(0,1) == 0 '
                  'else \'tails\'; print(result)" | tee /tmp/output'],
        file_outputs={'output': '/tmp/output'}
    )


def print_op(msg):
    """Print a message."""
    return dsl.ContainerOp(
        name='Print',
        image='alpine:3.6',
        command=['echo', msg],
    )


@dsl.pipeline(
    name='Conditional execution pipeline',
    description='Shows how to use dsl.Condition() and task dependencies on multiple condition branches.'
)
def flipcoin_pipeline():
    flip = flip_coin_op()
    cel_condition = CEL_ConditionOp("'%s' == 'heads'" % flip.output)
    with dsl.Condition(cel_condition.output == 'true'):
        random_num_head = random_num_op(0, 9)
        cel_condition_2 = CEL_ConditionOp("%s > 5" % random_num_head.output)
        with dsl.Condition(cel_condition_2.output == 'true'):
            print_op('heads and %s > 5!' % random_num_head.output)
        with dsl.Condition(cel_condition_2.output != 'true'):
            print_op('heads and %s <= 5!' % random_num_head.output)

    with dsl.Condition(cel_condition.output != 'true'):
        random_num_tail = random_num_op(10, 19)
        cel_condition_3 = CEL_ConditionOp("%s > 15" % random_num_tail.output)
        with dsl.Condition(cel_condition_3.output == 'true'):
            inner_task = print_op('tails and %s > 15!' % random_num_tail.output)
        with dsl.Condition(cel_condition_3.output != 'true'):
            print_op('tails and %s <= 15!' % random_num_tail.output)
    random_num_head2 = random_num_op(0, 9).after(random_num_head, random_num_tail, inner_task)


if __name__ == '__main__':
    from kfp_tekton.compiler import TektonCompiler
    import kfp_tekton
    pipeline_conf = kfp_tekton.compiler.pipeline_utils.TektonPipelineConf()
    pipeline_conf.add_pipeline_label('pipelines.kubeflow.org/cache_enabled', 'false')
    TektonCompiler().compile(flipcoin_pipeline, __file__.replace('.py', '.yaml'), tekton_pipeline_conf=pipeline_conf)

