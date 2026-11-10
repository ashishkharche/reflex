import React, { useReducer } from 'react';
import { Pressable, Text, View } from 'react-native';

// React Native screen over the plain JavaScript ViewModel. The component holds no count of its own.
// useReducer only forces a redraw after send.
export default function App({ vm }) {
  const [, redraw] = useReducer((n) => n + 1, 0);
  const send = (action) => { vm.send(action); redraw(); };
  return (
    <View>
      <Text testID="count">{String(vm.state.count)}</Text>
      <Pressable testID="minus" onPress={() => send({ type: 'decrement' })}><Text>−</Text></Pressable>
      <Pressable testID="plus" onPress={() => send({ type: 'increment' })}><Text>+</Text></Pressable>
      <Pressable testID="reset" onPress={() => send({ type: 'reset' })}><Text>Reset</Text></Pressable>
    </View>
  );
}
